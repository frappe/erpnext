# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import msgprint, _, scrub
from frappe.utils import cstr, cint, getdate, get_last_day
from calendar import monthrange
import datetime

def execute(filters=None):
	if not filters: filters = {}

	conditions, filters = get_conditions(filters)

	attendance_map = get_attendance_map(conditions, filters)
	employee_map = get_employee_details(filters)
	holiday_map = get_holiday_map(employee_map, filters.default_holiday_list,
		from_date=filters.from_date, to_date=filters.to_date)

	leave_types = frappe.db.sql_list("select name from `tabLeave Type` order by creation")

	columns = get_columns(filters, leave_types)

	data = []
	for employee in sorted(attendance_map):
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
		row['total_late_entry'] = 0
		row['total_early_exit'] = 0

		for day in range(filters["total_days_in_month"]):
			attendance_details = attendance_map.get(employee).get(day + 1, frappe._dict())
			attendance_date = datetime.date(year=filters.year, month=filters.month, day=day+1)

			attendance_status = attendance_details.get('status')
			if not attendance_status and is_holiday(attendance_date, holiday_map, employee_details, filters.default_holiday_list):
				attendance_status = "Holiday"

			day_fieldname = "day_{0}".format(day + 1)
			row["status_" + day_fieldname] = attendance_status
			row["attendance_" + day_fieldname] = attendance_details.name

			attendance_status_abbr = get_attendance_status_abbr(attendance_status, attendance_details.late_entry,
				attendance_details.early_exit)
			row[day_fieldname] = attendance_status_abbr

			if attendance_status == "Present":
				row['total_present'] += 1
			elif attendance_status == "Absent":
				row['total_absent'] += 1
			elif attendance_status == "On Leave":
				row['total_leave'] += 1
			elif attendance_status == "Half Day":
				row['total_present'] += 0.5
				row['total_absent'] += 0.5

			if attendance_details.late_entry:
				row['total_late_entry'] += 1
			if attendance_details.early_exit:
				row['total_early_exit'] += 1

		if not filters.get("employee"):
			filters.update({"employee": employee})
			conditions += " and employee = %(employee)s"
		elif not filters.get("employee") == employee:
			filters.update({"employee": employee})

		leave_details = frappe.db.sql("""
			select leave_type, status, count(*) as count
			from `tabAttendance`
			where ifnull(leave_type, '') != '' %s
			group by leave_type, status
		""" % conditions, filters, as_dict=1)

		leaves = {}
		for d in leave_details:
			if d.status == "Half Day":
				d.count = d.count * 0.5
			if d.leave_type in leaves:
				leaves[d.leave_type] += d.count
			else:
				leaves[d.leave_type] = d.count

		for leave_type in leave_types:
			leave_fieldname = "leave_{0}".format(scrub(leave_type))
			if leave_type in leaves:
				row[leave_fieldname] = leaves[leave_type]
			else:
				row[leave_fieldname] = 0.0

		data.append(row)
	return columns, data


def get_columns(filters, leave_types):
	columns = [
		{"fieldname": "employee", "label": _("Employee"), "fieldtype": "Link", "options": "Employee", "width": 80},
		{"fieldname": "employee_name", "label": _("Employee Name"), "fieldtype": "Data", "width": 140},
		{"fieldname": "designation", "label": _("Designation"), "fieldtype": "Link", "options": "Designation", "width": 120},
	]

	for day in range(filters["total_days_in_month"]):
		columns.append({"fieldname": "day_{0}".format(day+1), "label": day+1, "fieldtype": "Data", "width": 40,
			"day": cint(day+1)})

	columns += [
		{"fieldname": "total_present", "label": _("Present"), "fieldtype": "Float", "width": 70, "precision": 1},
		{"fieldname": "total_absent", "label": _("Absent"), "fieldtype": "Float", "width": 70, "precision": 1},
		{"fieldname": "total_leave", "label": _("On Leave"), "fieldtype": "Float", "width": 75, "precision": 1},
		{"fieldname": "total_late_entry", "label": _("Late Entry"), "fieldtype": "Float", "width": 80, "precision": 1},
		{"fieldname": "total_early_exit", "label": _("Early Exit"), "fieldtype": "Float", "width": 75, "precision": 1},
	]

	for leave_type in leave_types:
		leave_fieldname = "leave_{0}".format(scrub(leave_type))
		columns.append({"fieldname": leave_fieldname, "label": leave_type, "fieldtype": "Float", "precision": 1,
			"leave_type": leave_type})

	return columns


def get_attendance_map(conditions, filters):
	attendance_list = frappe.db.sql("""
		select name, employee, day(attendance_date) as day_of_month, attendance_date, status, late_entry, early_exit
		from tabAttendance
		where docstatus = 1 %s
		order by employee, attendance_date
	""" % conditions, filters, as_dict=1)

	attendance_map = {}
	for d in attendance_list:
		attendance_map.setdefault(d.employee, frappe._dict()).setdefault(d.day_of_month, frappe._dict())
		attendance_map[d.employee][d.day_of_month] = d

	return attendance_map


def get_conditions(filters):
	filters = frappe._dict(filters)

	if not (filters.get("month") and filters.get("year")):
		msgprint(_("Please select month and year"), raise_exception=1)

	if not filters.company:
		frappe.throw(_("Please select Company"))

	filters["year"] = cint(filters["year"])
	filters["month"] = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov",
		"Dec"].index(filters.month) + 1

	filters["total_days_in_month"] = monthrange(filters.year, filters.month)[1]
	filters["from_date"] = datetime.date(year=filters.year, month=filters.month, day=1)
	filters["to_date"] = get_last_day(filters["from_date"])

	filters["default_holiday_list"] = frappe.get_cached_value('Company', filters.company, "default_holiday_list")

	conditions = " and month(attendance_date) = %(month)s and year(attendance_date) = %(year)s"

	if filters.get("company"): conditions += " and company = %(company)s"
	if filters.get("employee"): conditions += " and employee = %(employee)s"

	return conditions, filters


def get_employee_details(filters):
	employee_map = frappe._dict()

	employee_condition = ""
	if filters.employee:
		employee_condition = " and name = %(employee)s"

	employees = frappe.db.sql("""
		select name, employee_name, designation, department, branch, company, holiday_list
		from tabEmployee
		where company = %(company)s {0}
	""".format(employee_condition), filters, as_dict=1)

	for d in employees:
		employee_map.setdefault(d.name, d)

	return employee_map


def is_holiday(attendance_date, holiday_map, employee_details, default_holiday_list):
	if holiday_map:
		emp_holiday_list = employee_details.holiday_list if employee_details.holiday_list else default_holiday_list
		if emp_holiday_list in holiday_map and getdate(attendance_date) in holiday_map[emp_holiday_list]:
			return True

	return False


def get_holiday_map(employee_map, default_holiday_list, from_date=None, to_date=None):
	holiday_lists = [employee_map[d]["holiday_list"] for d in employee_map if employee_map[d]["holiday_list"]]
	holiday_lists.append(default_holiday_list)
	holiday_lists = list(set(holiday_lists))
	holiday_map = get_holiday_map_from_holiday_lists(holiday_lists, from_date=from_date, to_date=to_date)
	return holiday_map


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
		ORDER BY YEAR(attendance_date) DESC
	""")
	if not year_list:
		year_list = [getdate().year]

	return "\n".join(str(year) for year in year_list)


def get_attendance_status_abbr(attendance_status, late_entry=0, early_exit=0):
	status_map = {"Present": "P", "Absent": "A", "Half Day": "HD", "On Leave": "L", "Holiday": "H"}

	abbr = status_map.get(attendance_status, '')
	if cint(late_entry):
		abbr = ">{0}".format(abbr)
	if cint(early_exit):
		abbr = "{0}<".format(abbr)

	return abbr
