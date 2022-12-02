# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import getdate, nowdate
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr


class Attendance(Document):
	def validate(self):
		from erpnext.controllers.status_updater import validate_status
		self.validate_attendance_date()
		self.validate_duplicate_record()
		self.check_leave_record()
		self.check_attendance_request_record()
		validate_status(self.status, ["Present", "Absent", "On Leave", "Half Day"])

	def before_validate_links(self):
		self.leave_application = None
		self.leave_type = None
		self.attendance_request = None

	def validate_duplicate_record(self):
		res = frappe.db.sql("""
			select name
			from `tabAttendance`
			where employee = %s and attendance_date = %s
			and name != %s and docstatus = 1
		""", (self.employee, getdate(self.attendance_date), self.name))
		if res:
			frappe.throw(_("Attendance for Employee {0} is already marked").format(self.employee))

	def check_leave_record(self):
		leave_record = frappe.db.sql("""
			select name, leave_type, half_day, half_day_date
			from `tabLeave Application`
			where employee = %s and %s between from_date and to_date and status = 'Approved' and docstatus = 1
		""", (self.employee, self.attendance_date), as_dict=True)

		if leave_record:
			for d in leave_record:
				self.leave_type = d.leave_type
				self.leave_application = d.name

				if d.half_day_date == getdate(self.attendance_date):
					if self.status != 'Half Day':
						frappe.msgprint(_("Employee {0} is on Half day on {1} based on Leave Application")
							.format(self.employee, self.attendance_date))
					self.status = 'Half Day'
				else:
					if self.status != 'On Leave':
						frappe.msgprint(_("Employee {0} is on Leave on {1} based on Leave Application")
							.format(self.employee, self.attendance_date))
					self.status = 'On Leave'
		else:
			self.leave_type = None
			self.leave_application = None

		if self.status == "On Leave" and not leave_record:
			frappe.throw(_("No leave record found for employee {0} for {1}").format(self.employee, self.attendance_date))

		self.previous_status = None

	def check_attendance_request_record(self):
		if self.leave_application:
			self.attendance_request = None
			return

		request_record = frappe.db.sql("""
			select name, half_day, half_day_date
			from `tabAttendance Request`
			where employee = %s and %s between from_date and to_date and docstatus = 1
		""", (self.employee, self.attendance_date), as_dict=True)

		if request_record:
			for d in request_record:
				self.attendance_request = d.name

				if d.half_day_date == getdate(self.attendance_date):
					if self.status != 'Half Day':
						frappe.msgprint(_("Employee {0} is on Half Day on {1} based on Attendance Request")
							.format(self.employee, self.attendance_date))
					self.status = 'Half Day'
				else:
					if self.status != 'Present':
						frappe.msgprint(_("Employee {0} is Presnet on {1} based on Attendance Request")
							.format(self.employee, self.attendance_date))
					self.status = 'Present'
		else:
			self.attendance_request = None

	def validate_attendance_date(self):
		date_of_joining = frappe.db.get_value("Employee", self.employee, "date_of_joining", cache=1)

		# leaves and attendance requests can be marked for future dates
		if getdate(self.attendance_date) > getdate(nowdate()):
			if self.status != 'On Leave' and not self.leave_application and not self.attendance_request:
				frappe.throw(_("Attendance can not be marked for future dates"))

		if date_of_joining and getdate(self.attendance_date) < getdate(date_of_joining):
			frappe.throw(_("Attendance date can not be before Employee's Joining Date"))


@frappe.whitelist()
def get_events(start, end, filters=None):
	events = []

	employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user})

	if not employee:
		return events

	from frappe.desk.reportview import get_filters_cond
	conditions = get_filters_cond("Attendance", filters, [])
	add_attendance(events, start, end, conditions=conditions)
	return events


def add_attendance(events, start, end, conditions=None):
	query = """select name, attendance_date, status
		from `tabAttendance` where
		attendance_date between %(from_date)s and %(to_date)s
		and docstatus = 1"""
	if conditions:
		query += conditions

	for d in frappe.db.sql(query, {"from_date":start, "to_date":end}, as_dict=True):
		e = {
			"name": d.name,
			"doctype": "Attendance",
			"start": d.attendance_date,
			"end": d.attendance_date,
			"title": cstr(d.status),
			"docstatus": d.docstatus
		}
		if e not in events:
			events.append(e)


def mark_absent(employee, attendance_date, shift=None):
	if not frappe.db.exists('Attendance', {'employee': employee, 'attendance_date': attendance_date, 'docstatus': 1}):
		doc_dict = {
			'doctype': 'Attendance',
			'employee': employee,
			'attendance_date': attendance_date,
			'status': 'Absent',
			'company': frappe.db.get_value("Employee", employee, "company", cache=1),
			'shift': shift
		}
		attendance = frappe.get_doc(doc_dict).insert()
		attendance.submit()
		return attendance.name
