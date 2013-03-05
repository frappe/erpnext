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

from webnotes.utils import add_days, getdate, now
from webnotes.model import db_exists
from webnotes.model.doc import make_autoname
from webnotes.model.bean import copy_doclist
from webnotes import msgprint

sql = webnotes.conn.sql
	


class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
		
	#autoname function
	def autoname(self):
		self.doc.name = make_autoname(self.doc.naming_series+'.#####')
	
	#get employee name based on employee id selected 
	def get_emp_name(self):
		emp_nm = sql("select employee_name from `tabEmployee` where name=%s", self.doc.employee)

		#this is done because sometimes user entered wrong employee name while uploading employee attendance
		webnotes.conn.set(self.doc, 'employee_name', emp_nm and emp_nm[0][0] or '')

		ret = { 'employee_name' : emp_nm and emp_nm[0][0] or ''}
		return ret
	
	#validation for duplicate record
	def validate_duplicate_record(self):	 
		res = sql("select name from `tabAttendance` where employee = '%s' and att_date = '%s' and not name = '%s' and docstatus = 1"%(self.doc.employee,self.doc.att_date, self.doc.name))
		if res:
			msgprint("Employee's attendance already marked.")
			raise Exception
			
	
	#check for already record present in leave transaction for same date
	def check_leave_record(self):
		if self.doc.status == 'Present':
			chk = sql("select name from `tabLeave Application` where employee=%s and (from_date <= %s and to_date >= %s) and docstatus!=2", (self.doc.employee, self.doc.att_date, self.doc.att_date))
			if chk:
				msgprint("Leave Application created for employee "+self.doc.employee+" whom you are trying to mark as 'Present' ")
				raise Exception
	
				 
	def validate_fiscal_year(self):
		from accounts.utils import validate_fiscal_year
		validate_fiscal_year(self.doc.att_date, self.doc.fiscal_year)
	
	def validate_att_date(self):
		import datetime
		if getdate(self.doc.att_date)>getdate(datetime.datetime.now().date().strftime('%Y-%m-%d')):
			msgprint("Attendance can not be marked for future dates")
			raise Exception

	# Validate employee
	#-------------------
	def validate_employee(self):
		emp = sql("select name, status from `tabEmployee` where name = '%s'" % self.doc.employee)
		if not emp:
			msgprint("Employee: %s does not exists in the system" % self.doc.employee, raise_exception=1)
		elif emp[0][1] != 'Active':
			msgprint("Employee: %s is not Active" % self.doc.employee, raise_exception=1)
			
	def validate(self):
		import utilities
		utilities.validate_status(self.doc.status, ["Present", "Absent", "Half Day"])

		self.validate_fiscal_year()
		self.validate_att_date()
		self.validate_duplicate_record()
		self.check_leave_record()
		
	def on_update(self):
		#self.validate()
		
		#this is done because sometimes user entered wrong employee name while uploading employee attendance
		x=self.get_emp_name()

	def on_submit(self):
		#this is done because while uploading attendance chnage docstatus to 1 i.e. submit
		webnotes.conn.set(self.doc,'docstatus',1)
		pass
