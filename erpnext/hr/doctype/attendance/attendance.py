# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import getdate, nowdate
from frappe import msgprint, _
from frappe.model.document import Document

class Attendance(Document):
	
	def validate_duplicate_record(self):	 
		res = frappe.db.sql("""select name from `tabAttendance` where employee = %s and att_date = %s 
			and name != %s and docstatus = 1""", 
			(self.employee, self.att_date, self.name))
		if res:
			msgprint(_("Attendance for the employee: ") + self.employee + 
				_(" already marked"), raise_exception=1)
			
	def check_leave_record(self):
		if self.status == 'Present':
			leave = frappe.db.sql("""select name from `tabLeave Application` 
				where employee = %s and %s between from_date and to_date and status = 'Approved' 
				and docstatus = 1""", (self.employee, self.att_date))
			
			if leave:
				frappe.msgprint(_("Employee: ") + self.employee + _(" was on leave on ")
					+ self.att_date + _(". You can not mark his attendance as 'Present'"), 
					raise_exception=1)
	
	def validate_fiscal_year(self):
		from erpnext.accounts.utils import validate_fiscal_year
		validate_fiscal_year(self.att_date, self.fiscal_year)
	
	def validate_att_date(self):
		if getdate(self.att_date) > getdate(nowdate()):
			msgprint(_("Attendance can not be marked for future dates"), raise_exception=1)

	def validate_employee(self):
		emp = frappe.db.sql("select name from `tabEmployee` where name = %s and status = 'Active'",
		 	self.employee)
		if not emp:
			msgprint(_("Employee: ") + self.employee + 
				_(" not active or does not exists in the system"), raise_exception=1)
			
	def validate(self):
		from erpnext.utilities import validate_status
		validate_status(self.status, ["Present", "Absent", "Half Day"])
		self.validate_fiscal_year()
		self.validate_att_date()
		self.validate_duplicate_record()
		self.check_leave_record()
		
	def on_update(self):
		# this is done because sometimes user entered wrong employee name 
		# while uploading employee attendance
		employee_name = frappe.db.get_value("Employee", self.employee, "employee_name")
		frappe.db.set(self, 'employee_name', employee_name)