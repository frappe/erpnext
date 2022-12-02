# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, cstr, add_days, get_weekday, format_time, formatdate, get_time
from erpnext.hr.utils import get_holiday_description
from erpnext.hr.report.monthly_attendance_sheet.monthly_attendance_sheet import get_employee_details,\
	get_attendance_status_abbr, get_holiday_map, is_date_holiday, get_employee_holiday_list,\
	get_attendance_from_checkins, is_in_employment_date, shift_ended
from erpnext.hr.doctype.holiday_list.holiday_list import get_default_holiday_list
from erpnext.hr.doctype.shift_assignment.shift_assignment import get_employee_shift


def execute(filters=None):
	filters = frappe._dict(filters)
	validate_filters(filters)

	checkin_map = get_employee_checkin_map(filters)
	attendance_map = get_attendance_map(filters)

	employees = list(set([e for e in checkin_map] + [e for e in attendance_map]))
	employees = sorted(employees)
	employee_map = get_employee_details(filters)

	holiday_map = get_holiday_map(employee_map, filters.default_holiday_list,
		from_date=filters.from_date, to_date=filters.to_date)

	data = []

	checkin_column_count = 1

	current_date = filters.from_date
	while current_date <= filters.to_date:
		day = get_weekday(current_date)
		for employee in employees:
			employee_details = employee_map.get(employee)
			if employee_details:
				row_template = frappe._dict({
					'date': current_date,
					'day': day,
					'employee': employee,
					'employee_name': employee_details.employee_name,
					'department': employee_details.department,
					'designation': employee_details.designation,
				})

				is_holiday = is_date_holiday(current_date, holiday_map, employee_details, filters.default_holiday_list)
				if is_holiday:
					row_template['attendance_status'] = "Holiday"
					row_template['attendance_abbr'] = get_attendance_status_abbr(row_template['attendance_status'])

					employee_holiday_list = get_employee_holiday_list(employee_details, filters.default_holiday_list)
					row_template['remarks'] = get_holiday_description(employee_holiday_list, current_date)

				checkin_shifts = checkin_map.get(employee, {}).get(current_date, {})
				attendance_shifts = attendance_map.get(employee, {}).get(current_date, {})

				shifts = list(set(list(checkin_shifts.keys()) + list(attendance_shifts.keys())))
				if not shifts and is_in_employment_date(current_date, employee_details):
					assigned_shift = get_employee_shift(employee, current_date, True)
					if assigned_shift:
						shifts.append(assigned_shift.shift_type.name)

				if shifts:
					for shift_type in shifts:
						row = row_template.copy()

						checkins = checkin_shifts.get(shift_type, [])
						attendance_details = attendance_shifts.get(shift_type, frappe._dict())

						checkin_column_count = max(checkin_column_count, len(checkins))

						for i, checkin_details in enumerate(checkins):
							checkin_time_fieldname = "checkin_time_{0}".format(i + 1)
							checkin_name_fieldname = "checkin_{0}".format(i + 1)
							row[checkin_name_fieldname] = checkin_details.name

							if getdate(checkin_details.time) != current_date:
								row[checkin_time_fieldname] = "{0} {1}".format(formatdate(checkin_details.time), format_time(checkin_details.time))
							else:
								row[checkin_time_fieldname] = format_time(checkin_details.time)

						if attendance_details:
							row['attendance'] = attendance_details.name
							row['attendance_status'] = attendance_details.status
							row['attendance_abbr'] = get_attendance_status_abbr(attendance_details.status, attendance_details.late_entry,
								attendance_details.early_exit)
							row['late_entry'] = attendance_details.late_entry
							row['early_exit'] = attendance_details.early_exit
							row['leave_type'] = attendance_details.leave_type
							row['leave_application'] = attendance_details.leave_application
							row['attendance_request'] = attendance_details.attendance_request
							row['remarks'] = attendance_details.remarks or attendance_details.leave_type or attendance_details.attendance_request_reason or row.remarks

							if attendance_details.working_hours:
								row['working_hours'] = attendance_details.working_hours

						row['attendance_marked'] = 1 if attendance_details else 0

						row['shift_type'] = shift_type
						if checkins:
							row['shift_start'] = get_time(checkins[0].shift_start) if checkins[0].shift_start else None
							row['shift_end'] = get_time(checkins[-1].shift_end) if checkins[-1].shift_end else None
						elif shift_type:
							shift_type_doc = frappe.get_cached_doc("Shift Type", shift_type)
							row['shift_start'] = get_time(shift_type_doc.start_time)
							row['shift_end'] = get_time(shift_type_doc.end_time)

						if not attendance_details and shift_type:
							if checkins:
								attendance_status, working_hours, late_entry, early_exit = get_attendance_from_checkins(checkins,
									shift_type)

								row['attendance_status'] = attendance_status
								row['attendance_abbr'] = get_attendance_status_abbr(attendance_status, late_entry, early_exit)
								row['late_entry'] = late_entry
								row['early_exit'] = early_exit
								if working_hours:
									row['working_hours'] = working_hours
							elif not is_holiday and shift_ended(shift_type, attendance_date=current_date):
								row['attendance_status'] = "Absent"

						data.append(row)
				else:
					data.append(row_template.copy())

		current_date = add_days(current_date, 1)

	columns = get_columns(filters, checkin_column_count)

	return columns, data


def validate_filters(filters):
	filters.from_date = getdate(filters.from_date)
	filters.to_date = getdate(filters.to_date)

	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date"))

	if not filters.company:
		frappe.throw(_("Please select Company"))

	filters.default_holiday_list = get_default_holiday_list(filters.company)


def get_employee_checkin_map(filters):
	employee_condition = ""
	if filters.employee:
		employee_condition = " and employee = %(employee)s"

	employee_checkins = frappe.db.sql("""
		select *
		from `tabEmployee Checkin`
		where (date(shift_start) between %(from_date)s and %(to_date)s or date(time) between %(from_date)s and %(to_date)s)
			{0}
		order by time
	""".format(employee_condition), filters, as_dict=1)

	employee_checkin_map = {}
	for d in employee_checkins:
		date = getdate(d.shift_start) if d.shift_start else getdate(d.time)
		employee_checkin_map.setdefault(d.employee, {}).setdefault(date, {}).setdefault(cstr(d.shift), []).append(d)

	return employee_checkin_map


def get_attendance_map(filters):
	employee_condition = ""
	if filters.employee:
		employee_condition = " and att.employee = %(employee)s"

	attendance = frappe.db.sql("""
		select att.name, att.employee, att.attendance_date, att.shift,
			att.status, att.late_entry, att.early_exit, att.working_hours,
			att.leave_application, att.attendance_request,
			att.remarks, att.leave_type, arq.reason as attendance_request_reason
		from `tabAttendance` att
		left join `tabAttendance Request` arq on arq.name = att.attendance_request
		where att.docstatus = 1 and att.attendance_date between %(from_date)s and %(to_date)s {0}
		order by attendance_date
	""".format(employee_condition), filters, as_dict=1)

	attendance_map = {}
	for d in attendance:
		date = getdate(d.attendance_date)
		attendance_map.setdefault(d.employee, {}).setdefault(date, {}).setdefault(cstr(d.shift), d)

	return attendance_map


def get_columns(filters, checkin_column_count):
	columns = [
		{"fieldname": "date", "label": _("Date"), "fieldtype": "Date", "width": 80},
		{"fieldname": "day", "label": _("Day"), "fieldtype": "Data", "width": 80},
		{"fieldname": "shift_type", "label": _("Shift"), "fieldtype": "Link", "options": "Shift Type", "width": 100},
		{"fieldname": "employee", "label": _("Employee"), "fieldtype": "Link", "options": "Employee", "width": 80},
		{"fieldname": "employee_name", "label": _("Employee Name"), "fieldtype": "Data", "width": 140},
		{"fieldname": "designation", "label": _("Designation"), "fieldtype": "Link", "options": "Designation", "width": 120},
		{"fieldname": "shift_start", "label": _("Shift Start"), "fieldtype": "Time", "width": 85},
		{"fieldname": "shift_end", "label": _("Shift End"), "fieldtype": "Time", "width": 85},
	]

	for i in range(checkin_column_count):
		checkin_time_fieldname = "checkin_time_{0}".format(i + 1)
		columns.append({
			"fieldname": checkin_time_fieldname,
			"label": _("Checkin {0}").format(i+1),
			"fieldtype": "Data",
			"width": 85,
			"checkin_idx": i + 1
		})

	columns += [
		{"fieldname": "attendance_status", "label": _("Status"), "fieldtype": "Data", "width": 75},
		{"fieldname": "remarks", "label": _("Remarks"), "fieldtype": "Data", "width": 100},
		{"fieldname": "working_hours", "label": _("Hours"), "fieldtype": "Float", "width": 60, "precision": 1},
		{"fieldname": "late_entry", "label": _("Late Entry"), "fieldtype": "Check", "width": 80},
		{"fieldname": "early_exit", "label": _("Early Exit"), "fieldtype": "Check", "width": 80},
		{"fieldname": "attendance_marked", "label": _("Marked"), "fieldtype": "Check", "width": 65},
		{"fieldname": "leave_application", "label": _("Leave Application"), "fieldtype": "Link", "options": "Leave Application", "width": 130},
		{"fieldname": "attendance_request", "label": _("Attendance Request"), "fieldtype": "Link", "options": "Attendance Request", "width": 140},
	]

	return columns
