# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes
from webnotes import _

from webnotes.utils import cint, cstr, date_diff, flt, formatdate, getdate
from webnotes.model import db_exists
from webnotes.model.wrapper import copy_doclist
from webnotes import form, msgprint

sql = webnotes.conn.sql
import datetime

class LeaveDayBlockedError(Exception): pass
	
class DocType:
	def __init__(self, doc, doclist):
		self.doc = doc
		self.doclist = doclist
		
	def validate(self):
		# if self.doc.leave_approver == self.doc.owner:
		self.validate_to_date()
		self.validate_balance_leaves()
		self.validate_leave_overlap()
		self.validate_max_days()
		#self.validate_block_days()
	
	def on_submit(self):
		if self.doc.status != "Approved":
			webnotes.msgprint("""Only Leave Applications with status 'Approved' can be Submitted.""",
				raise_exception=True)

	def validate_block_days(self):
		from_date = getdate(self.doc.from_date)
		to_date = getdate(self.doc.to_date)
		
		department = webnotes.conn.get_value("Employee", self.doc.employee, "department")
		if department:
			block_list = webnotes.conn.get_value("Department", department, "holiday_block_list")
			if block_list:
				for d in webnotes.conn.sql("""select block_date, reason from
					`tabHoliday Block List Date` where parent=%s""", block_list):
					block_date = getdate(d.block_date)
					if block_date > from_date and block_date < to_date:
						webnotes.msgprint(_("You cannot apply for a leave on the following date because it is blocked")
							+ ": " + formatdate(d.block_date) + _(" Reason: ") + d.reason)
						raise LeaveDayBlockedError

	def get_holidays(self):
		tot_hol = sql("""select count(*) from `tabHoliday` h1, `tabHoliday List` h2, `tabEmployee` e1 
			where e1.name = %s and h1.parent = h2.name and e1.holiday_list = h2.name 
			and h1.holiday_date between %s and %s""", (self.doc.employee, self.doc.from_date, self.doc.to_date))
		if not tot_hol:
			tot_hol = sql("""select count(*) from `tabHoliday` h1, `tabHoliday List` h2 
				where h1.parent = h2.name and h1.holiday_date between %s and %s
				and ifnull(h2.is_default,0) = 1 and h2.fiscal_year = %s""",
				(self.doc.from_date, self.doc.to_date, self.doc.fiscal_year))
		return tot_hol and flt(tot_hol[0][0]) or 0

	def get_total_leave_days(self):
		"""Calculates total leave days based on input and holidays"""
		ret = {'total_leave_days' : 0.5}
		if not self.doc.half_day:
			tot_days = date_diff(self.doc.to_date, self.doc.from_date) + 1
			holidays = self.get_holidays()
			ret = {
				'total_leave_days' : flt(tot_days)-flt(holidays)
			}
		return ret

	def validate_to_date(self):
		if self.doc.from_date and self.doc.to_date and \
				(getdate(self.doc.to_date) < getdate(self.doc.from_date)):
			msgprint("To date cannot be before from date")
			raise Exception
			
	def validate_balance_leaves(self):
		if self.doc.from_date and self.doc.to_date and not is_lwp(self.doc.leave_type):
			self.doc.leave_balance = get_leave_balance(self.doc.employee,
				self.doc.leave_type, self.doc.fiscal_year)["leave_balance"]
			self.doc.total_leave_days = self.get_total_leave_days()["total_leave_days"]
			
			if self.doc.leave_balance - self.doc.total_leave_days < 0:
				msgprint("There is not enough leave balance for Leave Type: %s" % \
					(self.doc.leave_type,), raise_exception=1)

	def validate_leave_overlap(self):
		for d in sql("""select name, leave_type, posting_date, from_date, to_date 
			from `tabLeave Application` 
			where 
			(from_date <= %(to_date)s and to_date >= %(from_date)s)
			and employee = %(employee)s
			and docstatus = 1 
			and name != %(name)s""", self.doc.fields, as_dict = 1):
 
			msgprint("Employee : %s has already applied for %s between %s and %s on %s. Please refer Leave Application : %s" % (self.doc.employee, cstr(d['leave_type']), formatdate(d['from_date']), formatdate(d['to_date']), formatdate(d['posting_date']), d['name']), raise_exception = 1)

	def validate_max_days(self):
		max_days = sql("select max_days_allowed from `tabLeave Type` where name = '%s'" %(self.doc.leave_type))
		max_days = max_days and flt(max_days[0][0]) or 0
		if max_days and self.doc.total_leave_days > max_days:
			msgprint("Sorry ! You cannot apply for %s for more than %s days" % (self.doc.leave_type, max_days))
			raise Exception


@webnotes.whitelist()
def get_leave_balance(employee, leave_type, fiscal_year):
	leave_all = webnotes.conn.sql("""select total_leaves_allocated 
		from `tabLeave Allocation` where employee = %s and leave_type = %s
		and fiscal_year = %s and docstatus = 1""", (employee, 
			leave_type, fiscal_year))
			
	leave_all = leave_all and flt(leave_all[0][0]) or 0
	
	leave_app = webnotes.conn.sql("""select SUM(total_leave_days) 
		from `tabLeave Application` 
		where employee = %s and leave_type = %s and fiscal_year = %s
		and docstatus = 1""", (employee, leave_type, fiscal_year))
	leave_app = leave_app and flt(leave_app[0][0]) or 0
	
	ret = {'leave_balance': leave_all - leave_app}
	return ret

@webnotes.whitelist()
def get_approver_list():
	roles = [r[0] for r in webnotes.conn.sql("""select distinct parent from `tabUserRole`
		where role='Leave Approver'""")]
	if not roles:
		webnotes.msgprint("No Leave Approvers. Please assign 'Leave Approver' Role to atleast one user.")
		
	return roles

def is_lwp(leave_type):
	lwp = sql("select is_lwp from `tabLeave Type` where name = %s", leave_type)
	return lwp and cint(lwp[0][0]) or 0