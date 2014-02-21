# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import getdate, nowdate
from frappe import msgprint, throw, _

class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist

	def validate_duplicate_record(self):
		res = frappe.conn.sql("""select name from `tabAttendance` where employee=%s and att_date=%s 
			and name!=%s and docstatus=1""", 
			(self.doc.employee, self.doc.att_date, self.doc.name))
		if res:
			throw("{attendance}: {employee} {marked}".format(**{
				"attendance": _("Attendance for the employee"),
				"employee": self.doc.employee,
				"marked": _("already marked")
			}))

	def check_leave_record(self):
		if self.doc.status == 'Present':
			leave = frappe.conn.sql("""select name from `tabLeave Application` 
				where employee=%s and %s between from_date and to_date and status = 'Approved' 
				and docstatus=1""", (self.doc.employee, self.doc.att_date))

			if leave:
				throw("{msg}: {emp} {leave} {date}. {cannot}".format(**{
					"msg": _("Employee"),
					"emp": self.doc.employee,
					"leave": _("was on leave on"),
					"date": self.doc.att_date,
					"cannot": _("You can not mark his attendance as 'Present'")
				}))

	def validate_att_date(self):
		if getdate(self.doc.att_date) > getdate(nowdate()):
			throw(_("Attendance can not be marked for future dates"))

	def validate_employee(self):
		emp = frappe.conn.sql("""select name from `tabEmployee` where name=%s and status='Active'""", 
		 	self.doc.employee)
		if not emp:
			throw("{msg}: {emp} {inactive}".format(**{
				"msg": _("Employee"),
				"emp": self.doc.employee,
				"inactive": _("not active or does not exists in the system")
			}))

	def validate(self):
		from erpnext.utilities import validate_status
		validate_status(self.doc.status, ["Present", "Absent", "Half Day"])
		self.validate_att_date()
		self.validate_duplicate_record()
		self.check_leave_record()

	def on_update(self):
		employee_name = frappe.conn.get_value("Employee", self.doc.employee, "employee_name")
		frappe.conn.set(self.doc, 'employee_name', employee_name)