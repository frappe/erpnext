# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import getdate, date_diff, add_days, nowdate
from erpnext.hr.doctype.employee.employee import is_holiday

class AttendanceRequest(Document):
	def validate(self):
		self.validate_date()

	def on_submit(self):
		self.create_attendance()

	def on_cancel(self):
		attendance_list = frappe.get_list("Attendance", {'employee': self.employee, 'attendance_request': self.name})
		if attendance_list:
			for attendance in attendance_list:
				attendance_obj = frappe.get_doc("Attendance", attendance['name'])
				attendance_obj.cancel()

	def validate_date(self):
		date_of_joining, relieving_date = frappe.db.get_value("Employee", self.employee, ["date_of_joining", "relieving_date"])
		if getdate(self.from_date) > getdate(self.to_date):
			frappe.throw(_("To date can not be less than from date"))
		elif getdate(self.from_date) > getdate(nowdate()):
			frappe.throw(_("Attendance request can not submit for future dates"))
		elif date_of_joining and getdate(self.from_date) < getdate(date_of_joining):
			frappe.throw(_("From date can not be less than employee's joining date"))
		elif relieving_date and getdate(self.to_date) > getdate(relieving_date):
			frappe.throw(_("To date can not greater than employee's relieving date"))

	def create_attendance(self):
		request_days = date_diff(self.to_date, self.from_date)
		for number in range(request_days):
			attendance_date = add_days(self.from_date, number)
			skip_attendance = self.validate_if_attendance_not_applicable(attendance_date)
			if not skip_attendance:
				attendance = frappe.new_doc("Attendance")
				attendance.employee = self.employee
				attendance.employee_name = self.employee_name
				attendance.status = "Present"
				attendance.attendance_date = attendance_date
				attendance.company = self.company
				attendance.attendance_request = self.name
				attendance.save(ignore_permissions=True)
				attendance.submit()

	def validate_if_attendance_not_applicable(self, attendance_date):
		# Check if attendance_date is a Holiday
		if is_holiday(self.employee, attendance_date):
			return True

		# Check if employee on Leave
		leave_record = frappe.db.sql("""select half_day from `tabLeave Application`
			where employee = %s and %s between from_date and to_date
			and docstatus = 1""", (self.employee, attendance_date), as_dict=True)
		if leave_record:
			return True

		return False
