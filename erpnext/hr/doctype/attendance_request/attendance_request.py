# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import date_diff, add_days, getdate, formatdate
from erpnext.hr.doctype.employee.employee import is_holiday
from erpnext.hr.utils import validate_dates, validate_overlap


class AttendanceRequest(Document):
	def validate(self):
		validate_dates(self, self.from_date, self.to_date, allow_future_date=True)
		validate_overlap(self, self.from_date, self.to_date, self.company)
		if self.half_day:
			if not getdate(self.from_date)<=getdate(self.half_day_date)<=getdate(self.to_date):
				frappe.throw(_("Half Day date should be in between from date and to date"))

	def on_submit(self):
		self.update_attendance()

	def on_cancel(self):
		self.cancel_attendance()

	def update_attendance(self):
		attendances_marked = 0

		request_days = date_diff(self.to_date, self.from_date) + 1
		for number in range(request_days):
			attendance_date = add_days(self.from_date, number)
			skip_attendance = self.validate_if_attendance_not_applicable(attendance_date)
			if not skip_attendance:
				if self.half_day and date_diff(getdate(self.half_day_date), getdate(attendance_date)) == 0:
					status = "Half Day"
				else:
					status = "Present"

				attendance_name = frappe.db.exists('Attendance', dict(employee=self.employee,
					attendance_date=attendance_date, docstatus=1))
				if attendance_name:
					# update existing attendance
					existing_doc = frappe.get_doc('Attendance', attendance_name)

					changes = {
						'status': status,
						'previous_status': existing_doc.status,
						'attendance_request': self.name
					}

					if self.remove_late_entry:
						changes.update({
							'late_entry': 0,
							'previous_late_entry': existing_doc.late_entry,
						})

					existing_doc.db_set(changes, notify=1)
				else:
					attendance = frappe.new_doc("Attendance")
					attendance.employee = self.employee
					attendance.employee_name = self.employee_name
					attendance.status = status
					attendance.attendance_date = attendance_date
					attendance.company = self.company
					attendance.attendance_request = self.name
					attendance.save(ignore_permissions=True)
					attendance.submit()

				attendances_marked += 1

		if not attendances_marked:
			frappe.throw(_("Cannot submit because no Attendance can be created in the date range"))

	def cancel_attendance(self):
		attendance_list = frappe.get_all("Attendance",
			{'employee': self.employee, 'attendance_request': self.name, 'docstatus': 1, 'status': ['!=', 'On Leave']})
		if attendance_list:
			for attendance in attendance_list:
				att_doc = frappe.get_doc("Attendance", attendance['name'])

				if att_doc.previous_status:
					changes = {
						'status': att_doc.previous_status,
						'previous_status': None,
						'attendance_request': None
					}
					if self.remove_late_entry:
						changes.update({
							'late_entry': att_doc.previous_late_entry,
							'previous_late_entry': 0,
						})
					att_doc.db_set(changes, notify=1)
				else:
					att_doc.flags.ignore_permissions = True
					att_doc.cancel()

	def validate_if_attendance_not_applicable(self, attendance_date):
		# Check if attendance_date is a Holiday
		if is_holiday(self.employee, attendance_date):
			frappe.msgprint(_("Attendance not created for {0} as it is a Holiday.")
				.format(formatdate(attendance_date)))
			return True

		# Check if employee on Leave
		leave_record = frappe.db.sql("""select half_day from `tabLeave Application`
			where employee = %s and %s between from_date and to_date
			and docstatus = 1""", (self.employee, attendance_date), as_dict=True)
		if leave_record:
			frappe.msgprint(_("Attendance not created for {0} as {1} is On Leave.")
				.format(formatdate(attendance_date), self.employee))
			return True

		existing_attendance = frappe.db.get_value("Attendance",
			{'employee': self.employee, 'attendance_date': attendance_date, 'docstatus': 1},
			['status', 'late_entry'], as_dict=1)
		if existing_attendance:
			if existing_attendance.status == "Present":
				if self.remove_late_entry:
					if not existing_attendance.late_entry:
						frappe.msgprint(_("Attendance not created for {0} as it is already marked Present without Late Entry.")
							.format(formatdate(attendance_date)))
						return True
				else:
					frappe.msgprint(_("Attendance not created for {0} as it is already marked Present.")
						.format(formatdate(attendance_date)))
					return True

			if existing_attendance.status == "Half Day" and self.half_day and date_diff(getdate(self.half_day_date), getdate(attendance_date)) == 0:
				frappe.msgprint(_("Attendance not created for {0} as it is already marked Half Day.")
					.format(formatdate(attendance_date)))
				return True

		return False
