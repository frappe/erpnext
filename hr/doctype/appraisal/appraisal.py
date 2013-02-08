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

from webnotes.utils import cstr, flt, getdate
from webnotes.model.wrapper import getlist
from webnotes.model.code import get_obj
from webnotes import msgprint

sql = webnotes.conn.sql


class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist

	def validate(self):
		if not self.doc.status:
			self.doc.status = "Draft"

		self.validate_dates()
		self.validate_existing_appraisal()
		self.calculate_total()

	def get_employee_name(self):
		emp_nm = sql("select employee_name from `tabEmployee` where name=%s", self.doc.employee)
		emp_nm= emp_nm and emp_nm[0][0] or ''
		self.doc.employee_name = emp_nm
		return emp_nm
	
	def fetch_kra(self):
		self.doclist = self.doc.clear_table(self.doclist,'appraisal_details')
		get_obj('DocType Mapper', 'Appraisal Template-Appraisal').dt_map('Appraisal Template', 'Appraisal', 
			self.doc.kra_template, self.doc, self.doclist, "[['Appraisal Template','Appraisal'],['Appraisal Template Goal', 'Appraisal Goal']]")
	
	def validate_dates(self):
		if getdate(self.doc.start_date) > getdate(self.doc.end_date):
			msgprint("End Date can not be less than Start Date")
			raise Exception
	
	def validate_existing_appraisal(self):
		chk = sql("""select name from `tabAppraisal` where employee=%s 
			and (status='Submitted' or status='Completed') 
			and ((start_date>=%s and start_date<=%s) 
			or (end_date>=%s and end_date<=%s))""",(self.doc.employee,self.doc.start_date,self.doc.end_date,self.doc.start_date,self.doc.end_date))
		if chk:
			msgprint("You have already created Appraisal "\
				+cstr(chk[0][0])+" in the current date range for employee "\
				+cstr(self.doc.employee_name))
			raise Exception
	
	def calculate_total(self):
		total, total_w  = 0, 0
		for d in getlist(self.doclist, 'appraisal_details'):
			if d.score:
				d.score_earned = flt(d.score) * flt(d.per_weightage) / 100
				total = total + d.score_earned
			total_w += flt(d.per_weightage)

		if int(total_w) != 100:
			msgprint("Total weightage assigned should be 100%. It is :" + str(total_w) + "%", 
				raise_exception=1)

		if webnotes.conn.get_value("Employee", self.doc.employee, "user_id") != \
				webnotes.session.user and total == 0:
			msgprint("Total can't be zero. You must atleast give some points!", raise_exception=1)

		self.doc.total_score = total
			
	def on_submit(self):
		webnotes.conn.set(self.doc, 'status', 'Submitted')
	
	def on_cancel(self): 
		webnotes.conn.set(self.doc, 'status', 'Cancelled')
