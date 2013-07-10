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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes

from webnotes.utils import getdate, nowdate
from webnotes import msgprint, _

sql = webnotes.conn.sql

class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
	
	def validate_duplicate_record(self):	 
		res = sql("""select name from `tabAttendance` where employee = %s and att_date = %s 
			and name != %s and docstatus = 1""", 
			(self.doc.employee, self.doc.att_date, self.doc.name))
		if res:
			msgprint(_("Attendance for the employee: ") + self.doc.employee + 
				_(" already marked"), raise_exception=1)
			
	def check_leave_record(self):
		if self.doc.status == 'Present':
			leave = sql("""select name from `tabLeave Application` 
				where employee = %s and %s between from_date and to_date and status = 'Approved' 
				and docstatus = 1""", (self.doc.employee, self.doc.att_date))
			
			if leave:
				webnotes.msgprint(_("Employee: ") + self.doc.employee + _(" was on leave on ")
					+ self.doc.att_date + _(". You can not mark his attendance as 'Present'"), 
					raise_exception=1)
	
	def validate_fiscal_year(self):
		from accounts.utils import validate_fiscal_year
		validate_fiscal_year(self.doc.att_date, self.doc.fiscal_year)
	
	def validate_att_date(self):
		if getdate(self.doc.att_date) > getdate(nowdate()):
			msgprint(_("Attendance can not be marked for future dates"), raise_exception=1)

	def validate_employee(self):
		emp = sql("select name from `tabEmployee` where name = %s and status = 'Active'",
		 	self.doc.employee)
		if not emp:
			msgprint(_("Employee: ") + self.doc.employee + 
				_(" not active or does not exists in the system"), raise_exception=1)
			
	def validate(self):
		import utilities
		utilities.validate_status(self.doc.status, ["Present", "Absent", "Half Day"])
		self.validate_fiscal_year()
		self.validate_att_date()
		self.validate_duplicate_record()
		self.check_leave_record()
		
	def on_update(self):
		# this is done because sometimes user entered wrong employee name 
		# while uploading employee attendance
		employee_name = webnotes.conn.get_value("Employee", self.doc.employee, "employee_name")
		webnotes.conn.set(self.doc, 'employee_name', employee_name)