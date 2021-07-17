# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe import _
from frappe.model.document import Document
from erpnext.hr.utils import validate_active_employee
from frappe.utils import cstr, get_datetime, formatdate, getdate, nowdate

class Attendance(Document):
	def validate(self):
		from erpnext.controllers.status_updater import validate_status
		validate_status(self.status, ["Present", "Absent", "On Leave", "Half Day", "Work From Home"])
		validate_active_employee(self.employee)
		self.validate_attendance_date()
		self.validate_duplicate_record()
		self.validate_employee_status()
		self.check_leave_record()
		self.set_overtime_type()
		self.set_default_shift()

		if not frappe.db.get_single_value("Payroll Settings", "fetch_standard_working_hours_from_shift_type"):
			self.standard_working_time = None

	def validate_attendance_date(self):
		date_of_joining = frappe.db.get_value("Employee", self.employee, "date_of_joining")

		# leaves can be marked for future dates
		if self.status != "On Leave" and not self.leave_application and getdate(self.attendance_date) > getdate(nowdate()):
			frappe.throw(_("Attendance can not be marked for future dates"))
		elif date_of_joining and getdate(self.attendance_date) < getdate(date_of_joining):
			frappe.throw(_("Attendance date can not be less than employee's joining date"))

	def validate_duplicate_record(self):
		res = frappe.db.sql("""
			select name from `tabAttendance`
			where employee = %s
				and attendance_date = %s
				and name != %s
				and docstatus != 2
		""", (self.employee, getdate(self.attendance_date), self.name))
		if res:
			frappe.throw(_("Attendance for employee {0} is already marked for the date {1}").format(
				frappe.bold(self.employee), frappe.bold(self.attendance_date)))

	def validate_employee_status(self):
		if frappe.db.get_value("Employee", self.employee, "status") == "Inactive":
			frappe.throw(_("Cannot mark attendance for an Inactive employee {0}").format(self.employee))

	def set_default_shift(self):
		if not self.shift:
			self.shift = get_shift_type(self.employee, self.attendance_date)

	def set_overtime_type(self):
		self.overtime_type = get_overtime_type(self.employee)

		if self.overtime_type:
			if frappe.db.get_single_value("Payroll Settings", "overtime_based_on") != "Attendance":
				frappe.msgprint(_('Set "Calculate Overtime Based On Attendance" to Attendance for Overtime Slip Creation'))

			maximum_overtime_hours_allowed = frappe.db.get_single_value("Payroll Settings", "maximum_overtime_hours_allowed")

			if maximum_overtime_hours_allowed and maximum_overtime_hours_allowed * 3600 < self.overtime_duration:
				self.overtime_duration = maximum_overtime_hours_allowed * 3600
				frappe.msgprint(_("Overtime Duration can not be greater than {0} Hours. You can change this in Payroll settings").format(
					str(maximum_overtime_hours_allowed)
				))

	def check_leave_record(self):
		leave_record = frappe.db.sql("""
			select leave_type, half_day, half_day_date
			from `tabLeave Application`
			where employee = %s
				and %s between from_date and to_date
				and status = 'Approved'
				and docstatus = 1
		""", (self.employee, self.attendance_date), as_dict=True)
		if leave_record:
			for d in leave_record:
				self.leave_type = d.leave_type
				if d.half_day_date == getdate(self.attendance_date):
					self.status = "Half Day"
					frappe.msgprint(_("Employee {0} on Half day on {1}")
						.format(self.employee, formatdate(self.attendance_date)))
				else:
					self.status = "On Leave"
					frappe.msgprint(_("Employee {0} is on Leave on {1}")
						.format(self.employee, formatdate(self.attendance_date)))

		if self.status in ("On Leave", "Half Day"):
			if not leave_record:
				frappe.msgprint(_("No leave record found for employee {0} on {1}")
					.format(self.employee, formatdate(self.attendance_date)), alert=1)
		elif self.leave_type:
			self.leave_type = None
			self.leave_application = None

	def validate_employee(self):
		emp = frappe.db.sql("select name from `tabEmployee` where name = %s and status = 'Active'",
		 	self.employee)
		if not emp:
			frappe.throw(_("Employee {0} is not active or does not exist").format(self.employee))

	def calculate_overtime_duration(self):
		#this method is only for Calculation of overtime based on Attendance through Employee Checkins
		self.overtime_duration = None

		if not self.standard_working_time and self.shift:
			self.standard_working_time = frappe.db.get_value("Shift Type", self.shift, "standard_working_time")

		if not self.overtime_type:
			self.overtime_type = get_overtime_type(self.employee)

		if int(self.working_time) > int(self.standard_working_time):
			self.overtime_duration = int(self.working_time) - int(self.standard_working_time)

@frappe.whitelist()
def get_shift_type(employee, attendance_date):
	emp_shift = frappe.db.get_value("Employee", employee, "default_shift")

	shift_assignment = frappe.db.sql('''SELECT name, shift_type
		FROM
			`tabShift Assignment`
		WHERE
			docstatus = 1
			AND employee = %(employee)s AND start_date <= %(attendance_date)s
			AND (end_date >= %(attendance_date)s OR end_date IS null)
			AND status = "Active"
		''', {
			"employee": employee,
			"attendance_date": attendance_date,
		}, as_dict = 1)

	if len(shift_assignment):
		shift = shift_assignment[0].shift_type
	else:
		shift = emp_shift

	return shift

@frappe.whitelist()
def get_overtime_type(employee):
	overtime_type = None
	emp_department = frappe.db.get_value("Employee", employee, "department")
	if emp_department:
		overtime_type_doc = frappe.get_list("Overtime Type", filters={
			"applicable_for": "Department", "department": emp_department}, fields=["name"])
		if len(overtime_type_doc):
			overtime_type = overtime_type_doc[0].name
	emp_grade = frappe.db.get_value("Employee", employee, "grade")

	if emp_grade:
		overtime_type_doc = frappe.get_list("Overtime Type", filters={
			"applicable_for": "Employee Grade", "employee_grade": emp_grade},
			fields=["name"])
		if len(overtime_type_doc):
			overtime_type = overtime_type_doc[0].name

	overtime_type_doc = frappe.get_list("Overtime Type", filters={
		"applicable_for": "Employee", "employee": employee}, fields=["name"])
	if len(overtime_type_doc):
		overtime_type = overtime_type_doc[0].name
	return overtime_type

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

def mark_attendance(employee, attendance_date, status, shift=None, leave_type=None, ignore_validate=False):
	if not frappe.db.exists('Attendance', {'employee':employee, 'attendance_date':attendance_date, 'docstatus':('!=', '2')}):
		company = frappe.db.get_value('Employee', employee, 'company')
		attendance = frappe.get_doc({
			'doctype': 'Attendance',
			'employee': employee,
			'attendance_date': attendance_date,
			'status': status,
			'company': company,
			'shift': shift,
			'leave_type': leave_type
		})
		attendance.flags.ignore_validate = ignore_validate
		attendance.insert()
		attendance.submit()
		return attendance.name

@frappe.whitelist()
def mark_bulk_attendance(data):
	import json
	if isinstance(data, frappe.string_types):
		data = json.loads(data)
	data = frappe._dict(data)
	company = frappe.get_value('Employee', data.employee, 'company')
	if not data.unmarked_days:
		frappe.throw(_("Please select a date."))
		return

	for date in data.unmarked_days:
		doc_dict = {
			'doctype': 'Attendance',
			'employee': data.employee,
			'attendance_date': get_datetime(date),
			'status': data.status,
			'company': company,
		}
		attendance = frappe.get_doc(doc_dict).insert()
		attendance.submit()


def get_month_map():
	return frappe._dict({
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
		"December": 12
		})

@frappe.whitelist()
def get_unmarked_days(employee, month):
	import calendar
	month_map = get_month_map()

	today = get_datetime()

	dates_of_month = ['{}-{}-{}'.format(today.year, month_map[month], r) for r in range(1, calendar.monthrange(today.year, month_map[month])[1] + 1)]

	length = len(dates_of_month)
	month_start, month_end = dates_of_month[0], dates_of_month[length-1]


	records = frappe.get_all("Attendance", fields = ["attendance_date", "employee"] , filters = [
		["attendance_date", ">=", month_start],
		["attendance_date", "<=", month_end],
		["employee", "=", employee],
		["docstatus", "!=", 2]
	])

	marked_days = [get_datetime(record.attendance_date) for record in records]
	unmarked_days = []

	for date in dates_of_month:
		date_time = get_datetime(date)
		if today.day == date_time.day and today.month == date_time.month:
			break
		if date_time not in marked_days:
			unmarked_days.append(date)

	return unmarked_days
