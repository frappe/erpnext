# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import msgprint, _, scrub
from frappe.utils import cstr, cint, getdate, get_last_day, add_months, today, formatdate
from erpnext.hr.doctype.holiday_list.holiday_list import get_default_holiday_list
from erpnext.hr.utils import get_employee_leave_policy
from erpnext.hr.doctype.shift_assignment.shift_assignment import get_employee_shift
from calendar import monthrange
import datetime
from collections import OrderedDict


def execute(filters=None):
	filters = frappe._dict(filters)

	validate_filters(filters)

	attendance_map = get_attendance_map(filters)
	checkin_map = get_employee_checkin_map(filters)

	employees = list(set([e for e in checkin_map] + [e for e in attendance_map]))
	employees = sorted(employees)
	employee_map = get_employee_details(filters)

	holiday_map = get_holiday_map(employee_map, filters.default_holiday_list,
		from_date=filters.from_date, to_date=filters.to_date)

	leave_type_map, leave_types = get_leave_type_map()

	data = []
	for employee in employees:
		employee_details = employee_map.get(employee)
		if not employee_details:
			continue

		row = frappe._dict({
			'employee': employee,
			'employee_name': employee_details.employee_name,
			'department': employee_details.department,
			'designation': employee_details.designation,
			'from_date': filters.from_date,
			'to_date': filters.to_date,
		})

		row['total_present'] = 0
		row['total_absent'] = 0
		row['total_leave'] = 0
		row['total_half_day'] = 0
		row['total_late_entry'] = 0
		row['total_early_exit'] = 0
		row['total_lwp'] = 0
		row['total_deduction'] = 0

		for day in range(1, filters["total_days_in_month"] + 1):
			attendance_date = datetime.date(year=filters.year, month=filters.month, day=day)
			is_holiday = is_date_holiday(attendance_date, holiday_map, employee_details, filters.default_holiday_list)

			attendance_details = attendance_map.get(employee, {}).get(day, frappe._dict())
			if not attendance_details:
				checkin_shifts = checkin_map.get(employee, {}).get(day, {})
				first_shift = list(checkin_shifts.keys())[0] if checkin_shifts else None
				checkins = checkin_shifts[first_shift] if first_shift else []

				if checkins:
					attendance_status, working_hours, late_entry, early_exit = get_attendance_from_checkins(checkins,
						first_shift)
					attendance_details.status = attendance_status
					attendance_details.late_entry = late_entry
					attendance_details.early_exit = early_exit
				elif not is_holiday and is_in_employment_date(attendance_date, employee_details):
					absent_shift = get_employee_shift(employee, attendance_date, True)
					if absent_shift and shift_ended(absent_shift.shift_type.name, attendance_date=attendance_date):
						attendance_details.status = "Absent"

			attendance_status = attendance_details.get('status')
			if not attendance_status and is_holiday:
				attendance_status = "Holiday"

			day_fieldname = "day_{0}".format(day)
			row["status_" + day_fieldname] = attendance_status
			row["attendance_" + day_fieldname] = attendance_details.name

			attendance_status_abbr = get_attendance_status_abbr(attendance_status, attendance_details.late_entry,
				attendance_details.early_exit, attendance_details.leave_type)
			row[day_fieldname] = attendance_status_abbr

			if attendance_status == "Present":
				row['total_present'] += 1

				if attendance_details.late_entry:
					row['total_late_entry'] += 1
				if attendance_details.early_exit:
					row['total_early_exit'] += 1
			elif attendance_status == "Absent":
				row['total_absent'] += 1
				row['total_deduction'] += 1
			elif attendance_status == "Half Day":
				row['total_half_day'] += 1
				if not attendance_details.leave_type:
					row['total_deduction'] += 0.5
			elif attendance_status == "On Leave":
				leave_details = leave_type_map.get(attendance_details.leave_type, frappe._dict())
				if not is_holiday or leave_details.include_holidays:
					row['total_leave'] += 1

			if attendance_status in ("On Leave", "Half Day") and attendance_details.leave_type:
				leave_details = leave_type_map.get(attendance_details.leave_type, frappe._dict())
				leave_details.has_entry = True

				leave_fieldname = "leave_{0}".format(scrub(leave_details.name))
				leave_count = 0.5 if attendance_status == "Half Day" else 1

				if not is_holiday or leave_details.include_holidays:
					row.setdefault(leave_fieldname, 0)
					row[leave_fieldname] += leave_count

					if leave_details.is_lwp:
						row['total_deduction'] += leave_count
						row['total_lwp'] += leave_count

		row['total_late_deduction'] = 0

		leave_policy = get_employee_leave_policy(employee)
		if leave_policy:
			row['total_late_deduction'] = leave_policy.get_lwp_from_late_days(row['total_late_entry'])
			row['total_deduction'] += row['total_late_deduction']

		data.append(row)

	if data:
		days_row = frappe._dict({})
		for day in range(1, filters["total_days_in_month"] + 1):
			attendance_date = datetime.date(year=filters.year, month=filters.month, day=day)
			day_fieldname = "day_{0}".format(day)
			day_of_the_week = formatdate(attendance_date, "EE")
			days_row[day_fieldname] = day_of_the_week
			days_row.is_day_row = 1

		data.insert(0, days_row)

	columns = get_columns(filters, leave_types)
	return columns, data


def get_columns(filters, leave_types):
	columns = [
		{"fieldname": "employee", "label": _("Employee"), "fieldtype": "Link", "options": "Employee", "width": 80},
		{"fieldname": "employee_name", "label": _("Employee Name"), "fieldtype": "Data", "width": 140},
		{"fieldname": "designation", "label": _("Designation"), "fieldtype": "Link", "options": "Designation", "width": 100},
	]

	for day in range(1, filters["total_days_in_month"] + 1):
		columns.append({"fieldname": "day_{0}".format(day), "label": cstr(day), "fieldtype": "Data", "width": 40,
			"day": cint(day)})

	columns += [
		{"fieldname": "total_present", "label": _("Present"), "fieldtype": "Float", "width": 70, "precision": 1},
		{"fieldname": "total_absent", "label": _("Absent"), "fieldtype": "Float", "width": 70, "precision": 1},
		{"fieldname": "total_half_day", "label": _("Half Day"), "fieldtype": "Float", "width": 75, "precision": 1},
		{"fieldname": "total_leave", "label": _("On Leave"), "fieldtype": "Float", "width": 75, "precision": 1},
		{"fieldname": "total_late_entry", "label": _("Late Entry"), "fieldtype": "Float", "width": 80, "precision": 1},
		{"fieldname": "total_early_exit", "label": _("Early Exit"), "fieldtype": "Float", "width": 75, "precision": 1},
	]

	columns.append({"fieldname": "total_late_deduction", "label": _("Late Deduction"), "fieldtype": "Float", "width": 110, "precision": 1})

	columns.append({"fieldname": "total_deduction", "label": _("Total Deduction"), "fieldtype": "Float", "width": 112, "precision": 1})

	for leave_type in leave_types:
		if leave_type.has_entry:
			leave_fieldname = "leave_{0}".format(scrub(leave_type.name))
			columns.append({"fieldname": leave_fieldname, "label": leave_type.name, "fieldtype": "Float", "precision": 1,
				"leave_type": leave_type.name, "is_lwp": cint(leave_type.is_lwp)})

	return columns


def get_attendance_map(filters):
	conditions = get_conditions(filters)

	attendance_list = frappe.db.sql("""
		select name, employee, day(attendance_date) as day_of_month, attendance_date,
			status, late_entry, early_exit, leave_type
		from tabAttendance
		where docstatus = 1 and attendance_date between %(from_date)s and %(to_date)s {0}
		order by employee, attendance_date
	""".format(conditions), filters, as_dict=1)

	attendance_map = {}
	for d in attendance_list:
		attendance_map.setdefault(d.employee, frappe._dict()).setdefault(d.day_of_month, frappe._dict())
		attendance_map[d.employee][d.day_of_month] = d

	return attendance_map


def get_employee_checkin_map(filters):
	conditions = get_conditions(filters)

	employee_checkins = frappe.db.sql("""
		select *, day(shift_start) as day_of_month
		from `tabEmployee Checkin`
		where date(shift_start) between %(from_date)s and %(to_date)s
			and ifnull(attendance, '') = ''
			and ifnull(shift, '') != ''
			{0}
		order by time
	""".format(conditions), filters, as_dict=1)

	employee_checkin_map = {}
	for d in employee_checkins:
		employee_checkin_map.setdefault(d.employee, {})\
			.setdefault(d.day_of_month, OrderedDict())\
			.setdefault(cstr(d.shift), [])\
			.append(d)

	return employee_checkin_map


def validate_filters(filters):
	if not (filters.get("month") and filters.get("year")):
		msgprint(_("Please select month and year"), raise_exception=1)

	if not filters.company:
		frappe.throw(_("Please select Company"))

	filters["year"] = cint(filters["year"])
	filters["month"] = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]\
		.index(filters.month) + 1

	filters["total_days_in_month"] = monthrange(filters.year, filters.month)[1]
	filters["from_date"] = datetime.date(year=filters.year, month=filters.month, day=1)
	filters["to_date"] = get_last_day(filters["from_date"])

	filters["default_holiday_list"] = get_default_holiday_list(filters.company)


def get_conditions(filters):
	conditions = ""
	if filters.get("employee"):
		conditions += " and employee = %(employee)s"

	return conditions


def get_employee_details(filters):
	employee_map = frappe._dict()

	employee_condition = ""
	if filters.employee:
		employee_condition = " and name = %(employee)s"

	employees = frappe.db.sql("""
		select name, employee_name,
			designation, department, branch, company,
			date_of_joining, relieving_date, creation, holiday_list
		from tabEmployee
		where company = %(company)s {0}
	""".format(employee_condition), filters, as_dict=1)

	for d in employees:
		employee_map.setdefault(d.name, d)

	return employee_map


def is_date_holiday(attendance_date, holiday_map, employee_details, default_holiday_list):
	if holiday_map:
		emp_holiday_list = get_employee_holiday_list(employee_details, default_holiday_list)
		if emp_holiday_list in holiday_map and getdate(attendance_date) in holiday_map[emp_holiday_list]:
			return True

	return False


def get_employee_holiday_list(employee_details, default_holiday_list):
	return employee_details.holiday_list if employee_details.holiday_list else default_holiday_list


def get_holiday_map(employee_map, default_holiday_list, from_date=None, to_date=None):
	holiday_lists = [employee_map[d]["holiday_list"] for d in employee_map if employee_map[d]["holiday_list"]]
	holiday_lists.append(default_holiday_list)
	holiday_lists = list(set(holiday_lists))
	holiday_map = get_holiday_map_from_holiday_lists(holiday_lists, from_date=from_date, to_date=to_date)
	return holiday_map


def is_in_employment_date(attendance_date, employee_details):
	start_date = employee_details.date_of_joining or employee_details.creation
	start_date = getdate(start_date) if start_date else None
	end_date = getdate(employee_details.relieving_date) if employee_details.relieving_date else None

	if not start_date or attendance_date < start_date:
		return False
	elif end_date and attendance_date > end_date:
		return False
	else:
		return True


def get_leave_type_map():
	leave_types = frappe.db.sql("""
		select name, is_lwp, include_holiday
		from `tabLeave Type`
		order by idx, creation
	""", as_dict=1)

	leave_type_map = {}
	for d in leave_types:
		leave_type_map[d.name] = d

	return leave_type_map, leave_types


def get_holiday_map_from_holiday_lists(holiday_lists, from_date=None, to_date=None):
	holiday_map = frappe._dict()

	date_condition = ""
	if from_date:
		date_condition += " and holiday_date >= %(from_date)s"
	if to_date:
		date_condition += " and holiday_date <= %(to_date)s"

	for holiday_list in holiday_lists:
		if holiday_list:
			args = {'holiday_list': holiday_list, 'from_date': from_date, 'to_date': to_date}
			holidays = frappe.db.sql_list("""
				select holiday_date
				from `tabHoliday`
				where parent=%(holiday_list)s {0}
				order by holiday_date
			""".format(date_condition), args)

			holiday_map.setdefault(holiday_list, holidays)

	return holiday_map


@frappe.whitelist()
def get_attendance_years():
	year_list = frappe.db.sql_list("""
		select distinct YEAR(attendance_date)
		from tabAttendance
		where docstatus = 1
	""")

	if not year_list:
		year_list = []

	year_list.append(getdate().year)
	year_list.append(getdate(add_months(today(), -1)).year)

	year_list = list(set(year_list))
	year_list = sorted(year_list, reverse=True)

	return "\n".join(str(year) for year in year_list)


def get_attendance_status_abbr(attendance_status, late_entry=0, early_exit=0, leave_type=None):
	status_map = {"Present": "P", "Absent": "A", "Half Day": "HD", "On Leave": "L", "Holiday": "H"}

	abbr = status_map.get(attendance_status, '')

	leave_type_abbr = ""
	if leave_type:
		leave_type_abbr = frappe.get_cached_value("Leave Type", leave_type, "abbr")
	if not leave_type_abbr:
		leave_type_abbr = status_map['On Leave']

	if attendance_status == "On Leave":
		abbr = leave_type_abbr

	# if attendance_status == "Half Day" and leave_type:
	# 	abbr = "{0}({1})".format(abbr, leave_type_abbr)

	if cint(late_entry):
		abbr = ">{0}".format(abbr)
	if cint(early_exit):
		abbr = "{0}<".format(abbr)

	return abbr


def get_attendance_from_checkins(checkins, shift):
	shift_doc = frappe.get_cached_doc("Shift Type", shift)

	ignore_working_hour_threshold = not shift_ended(shift, checkins)
	return shift_doc.get_attendance(checkins, ignore_working_hour_threshold=ignore_working_hour_threshold)


def shift_ended(shift, checkins=None, attendance_date=None):
	if not shift:
		return False

	last_sync_of_checkin = frappe.db.get_value("Shift Type", shift, "last_sync_of_checkin", cache=1)
	if not last_sync_of_checkin:
		return False

	if checkins is None:
		if attendance_date:
			return getdate(attendance_date) < getdate(last_sync_of_checkin)
		else:
			return False
	else:
		shift_not_ended = [chk for chk in checkins if last_sync_of_checkin < chk.shift_actual_end]
		return not shift_not_ended
