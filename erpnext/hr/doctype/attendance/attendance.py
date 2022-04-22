# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import Criterion
from frappe.utils import cint, cstr, formatdate, get_datetime, get_link_to_form, getdate, nowdate

from erpnext.hr.doctype.shift_assignment.shift_assignment import has_overlapping_timings
from erpnext.hr.utils import get_holiday_dates_for_employee, validate_active_employee


class DuplicateAttendanceError(frappe.ValidationError):
	pass


class OverlappingShiftAttendanceError(frappe.ValidationError):
	pass


class Attendance(Document):
	def validate(self):
		from erpnext.controllers.status_updater import validate_status

		validate_status(self.status, ["Present", "Absent", "On Leave", "Half Day", "Work From Home"])
		validate_active_employee(self.employee)
		self.validate_attendance_date()
		self.validate_duplicate_record()
		self.validate_overlapping_shift_attendance()
		self.validate_employee_status()
		self.check_leave_record()

	def validate_attendance_date(self):
		date_of_joining = frappe.db.get_value("Employee", self.employee, "date_of_joining")

		# leaves can be marked for future dates
		if (
			self.status != "On Leave"
			and not self.leave_application
			and getdate(self.attendance_date) > getdate(nowdate())
		):
			frappe.throw(_("Attendance can not be marked for future dates"))
		elif date_of_joining and getdate(self.attendance_date) < getdate(date_of_joining):
			frappe.throw(_("Attendance date can not be less than employee's joining date"))

	def validate_duplicate_record(self):
		duplicate = get_duplicate_attendance_record(
			self.employee, self.attendance_date, self.shift, self.name
		)

		if duplicate:
			frappe.throw(
				_("Attendance for employee {0} is already marked for the date {1}: {2}").format(
					frappe.bold(self.employee),
					frappe.bold(self.attendance_date),
					get_link_to_form("Attendance", duplicate[0].name),
				),
				title=_("Duplicate Attendance"),
				exc=DuplicateAttendanceError,
			)

	def validate_overlapping_shift_attendance(self):
		attendance = get_overlapping_shift_attendance(
			self.employee, self.attendance_date, self.shift, self.name
		)

		if attendance:
			frappe.throw(
				_("Attendance for employee {0} is already marked for an overlapping shift {1}: {2}").format(
					frappe.bold(self.employee),
					frappe.bold(attendance.shift),
					get_link_to_form("Attendance", attendance.name),
				),
				title=_("Overlapping Shift Attendance"),
				exc=OverlappingShiftAttendanceError,
			)

	def validate_employee_status(self):
		if frappe.db.get_value("Employee", self.employee, "status") == "Inactive":
			frappe.throw(_("Cannot mark attendance for an Inactive employee {0}").format(self.employee))

	def check_leave_record(self):
		leave_record = frappe.db.sql(
			"""
			select leave_type, half_day, half_day_date
			from `tabLeave Application`
			where employee = %s
				and %s between from_date and to_date
				and status = 'Approved'
				and docstatus = 1
		""",
			(self.employee, self.attendance_date),
			as_dict=True,
		)
		if leave_record:
			for d in leave_record:
				self.leave_type = d.leave_type
				if d.half_day_date == getdate(self.attendance_date):
					self.status = "Half Day"
					frappe.msgprint(
						_("Employee {0} on Half day on {1}").format(self.employee, formatdate(self.attendance_date))
					)
				else:
					self.status = "On Leave"
					frappe.msgprint(
						_("Employee {0} is on Leave on {1}").format(self.employee, formatdate(self.attendance_date))
					)

		if self.status in ("On Leave", "Half Day"):
			if not leave_record:
				frappe.msgprint(
					_("No leave record found for employee {0} on {1}").format(
						self.employee, formatdate(self.attendance_date)
					),
					alert=1,
				)
		elif self.leave_type:
			self.leave_type = None
			self.leave_application = None

	def validate_employee(self):
		emp = frappe.db.sql(
			"select name from `tabEmployee` where name = %s and status = 'Active'", self.employee
		)
		if not emp:
			frappe.throw(_("Employee {0} is not active or does not exist").format(self.employee))


def get_duplicate_attendance_record(employee, attendance_date, shift, name=None):
	attendance = frappe.qb.DocType("Attendance")
	query = (
		frappe.qb.from_(attendance)
		.select(attendance.name)
		.where((attendance.employee == employee) & (attendance.docstatus < 2))
	)

	if shift:
		query = query.where(
			Criterion.any(
				[
					Criterion.all(
						[
							((attendance.shift.isnull()) | (attendance.shift == "")),
							(attendance.attendance_date == attendance_date),
						]
					),
					Criterion.all(
						[
							((attendance.shift.isnotnull()) | (attendance.shift != "")),
							(attendance.attendance_date == attendance_date),
							(attendance.shift == shift),
						]
					),
				]
			)
		)
	else:
		query = query.where((attendance.attendance_date == attendance_date))

	if name:
		query = query.where(attendance.name != name)

	return query.run(as_dict=True)


def get_overlapping_shift_attendance(employee, attendance_date, shift, name=None):
	if not shift:
		return {}

	attendance = frappe.qb.DocType("Attendance")
	query = (
		frappe.qb.from_(attendance)
		.select(attendance.name, attendance.shift)
		.where(
			(attendance.employee == employee)
			& (attendance.docstatus < 2)
			& (attendance.attendance_date == attendance_date)
			& (attendance.shift != shift)
		)
	)

	if name:
		query = query.where(attendance.name != name)

	overlapping_attendance = query.run(as_dict=True)

	if overlapping_attendance and has_overlapping_timings(shift, overlapping_attendance[0].shift):
		return overlapping_attendance[0]
	return {}


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
		and docstatus < 2"""
	if conditions:
		query += conditions

	for d in frappe.db.sql(query, {"from_date": start, "to_date": end}, as_dict=True):
		e = {
			"name": d.name,
			"doctype": "Attendance",
			"start": d.attendance_date,
			"end": d.attendance_date,
			"title": cstr(d.status),
			"docstatus": d.docstatus,
		}
		if e not in events:
			events.append(e)


def mark_attendance(
	employee,
	attendance_date,
	status,
	shift=None,
	leave_type=None,
	ignore_validate=False,
	late_entry=False,
	early_exit=False,
):
	if get_duplicate_attendance_record(employee, attendance_date, shift):
		return

	if get_overlapping_shift_attendance(employee, attendance_date, shift):
		return

	company = frappe.db.get_value("Employee", employee, "company")
	attendance = frappe.get_doc(
		{
			"doctype": "Attendance",
			"employee": employee,
			"attendance_date": attendance_date,
			"status": status,
			"company": company,
			"shift": shift,
			"leave_type": leave_type,
			"late_entry": late_entry,
			"early_exit": early_exit,
		}
	)
	attendance.flags.ignore_validate = ignore_validate
	attendance.insert()
	attendance.submit()
	return attendance.name


@frappe.whitelist()
def mark_bulk_attendance(data):
	import json

	if isinstance(data, str):
		data = json.loads(data)
	data = frappe._dict(data)
	company = frappe.get_value("Employee", data.employee, "company")
	if not data.unmarked_days:
		frappe.throw(_("Please select a date."))
		return

	for date in data.unmarked_days:
		doc_dict = {
			"doctype": "Attendance",
			"employee": data.employee,
			"attendance_date": get_datetime(date),
			"status": data.status,
			"company": company,
		}
		attendance = frappe.get_doc(doc_dict).insert()
		attendance.submit()


def get_month_map():
	return frappe._dict(
		{
			"January": 1,
			"February": 2,
			"March": 3,
			"April": 4,
			"May": 5,
			"June": 6,
			"July": 7,
			"August": 8,
			"September": 9,
			"October": 10,
			"November": 11,
			"December": 12,
		}
	)


@frappe.whitelist()
def get_unmarked_days(employee, month, exclude_holidays=0):
	import calendar

	month_map = get_month_map()
	today = get_datetime()

	joining_date, relieving_date = frappe.get_cached_value(
		"Employee", employee, ["date_of_joining", "relieving_date"]
	)
	start_day = 1
	end_day = calendar.monthrange(today.year, month_map[month])[1] + 1

	if joining_date and joining_date.month == month_map[month]:
		start_day = joining_date.day

	if relieving_date and relieving_date.month == month_map[month]:
		end_day = relieving_date.day + 1

	dates_of_month = [
		"{}-{}-{}".format(today.year, month_map[month], r) for r in range(start_day, end_day)
	]
	month_start, month_end = dates_of_month[0], dates_of_month[-1]

	records = frappe.get_all(
		"Attendance",
		fields=["attendance_date", "employee"],
		filters=[
			["attendance_date", ">=", month_start],
			["attendance_date", "<=", month_end],
			["employee", "=", employee],
			["docstatus", "!=", 2],
		],
	)

	marked_days = [get_datetime(record.attendance_date) for record in records]
	if cint(exclude_holidays):
		holiday_dates = get_holiday_dates_for_employee(employee, month_start, month_end)
		holidays = [get_datetime(record) for record in holiday_dates]
		marked_days.extend(holidays)

	unmarked_days = []

	for date in dates_of_month:
		date_time = get_datetime(date)
		if today.day <= date_time.day and today.month <= date_time.month:
			break
		if date_time not in marked_days:
			unmarked_days.append(date)

	return unmarked_days
