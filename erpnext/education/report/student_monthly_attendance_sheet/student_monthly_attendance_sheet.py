# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.utils import add_days, cstr, date_diff, get_first_day, get_last_day, getdate

from erpnext.education.api import get_student_group_students
from erpnext.education.doctype.student_attendance.student_attendance import get_holiday_list
from erpnext.support.doctype.issue.issue import get_holidays


def execute(filters=None):
	if not filters:
		filters = {}

	from_date = get_first_day(filters["month"] + "-" + filters["year"])
	to_date = get_last_day(filters["month"] + "-" + filters["year"])
	total_days_in_month = date_diff(to_date, from_date) + 1
	columns = get_columns(total_days_in_month)
	students = get_student_group_students(filters.get("student_group"), 1)
	students_list = get_students_list(students)
	att_map = get_attendance_list(from_date, to_date, filters.get("student_group"), students_list)
	data = []

	for stud in students:
		row = [stud.student, stud.student_name]
		student_status = frappe.db.get_value("Student", stud.student, "enabled")
		date = from_date
		total_p = total_a = 0.0

		for day in range(total_days_in_month):
			status = "None"

			if att_map.get(stud.student):
				status = att_map.get(stud.student).get(date, "None")
			elif not student_status:
				status = "Inactive"
			else:
				status = "None"

			status_map = {"Present": "P", "Absent": "A", "None": "", "Inactive": "-", "Holiday": "H"}
			row.append(status_map[status])

			if status == "Present":
				total_p += 1
			elif status == "Absent":
				total_a += 1
			date = add_days(date, 1)

		row += [total_p, total_a]
		data.append(row)
	return columns, data


def get_columns(days_in_month):
	columns = [_("Student") + ":Link/Student:90", _("Student Name") + "::150"]
	for day in range(days_in_month):
		columns.append(cstr(day + 1) + "::20")
	columns += [_("Total Present") + ":Int:95", _("Total Absent") + ":Int:90"]
	return columns


def get_students_list(students):
	student_list = []
	for stud in students:
		student_list.append(stud.student)
	return student_list


def get_attendance_list(from_date, to_date, student_group, students_list):
	attendance_list = frappe.db.sql(
		"""select student, date, status
		from `tabStudent Attendance` where student_group = %s
		and docstatus = 1
		and date between %s and %s
		order by student, date""",
		(student_group, from_date, to_date),
		as_dict=1,
	)

	att_map = {}
	students_with_leave_application = get_students_with_leave_application(
		from_date, to_date, students_list
	)
	for d in attendance_list:
		att_map.setdefault(d.student, frappe._dict()).setdefault(d.date, "")

		if students_with_leave_application.get(
			d.date
		) and d.student in students_with_leave_application.get(d.date):
			att_map[d.student][d.date] = "Present"
		else:
			att_map[d.student][d.date] = d.status

	att_map = mark_holidays(att_map, from_date, to_date, students_list)

	return att_map


def get_students_with_leave_application(from_date, to_date, students_list):
	if not students_list:
		return
	leave_applications = frappe.db.sql(
		"""
		select student, from_date, to_date
		from `tabStudent Leave Application`
		where
			mark_as_present = 1 and docstatus = 1
			and student in %(students)s
			and (
				from_date between %(from_date)s and %(to_date)s
				or to_date between %(from_date)s and %(to_date)s
				or (%(from_date)s between from_date and to_date and %(to_date)s between from_date and to_date)
			)
		""",
		{"students": students_list, "from_date": from_date, "to_date": to_date},
		as_dict=True,
	)
	students_with_leaves = {}
	for application in leave_applications:
		for date in daterange(application.from_date, application.to_date):
			students_with_leaves.setdefault(date, []).append(application.student)

	return students_with_leaves


def daterange(d1, d2):
	import datetime

	return (d1 + datetime.timedelta(days=i) for i in range((d2 - d1).days + 1))


@frappe.whitelist()
def get_attendance_years():
	year_list = frappe.db.sql_list(
		"""select distinct YEAR(date) from `tabStudent Attendance` ORDER BY YEAR(date) DESC"""
	)
	if not year_list:
		year_list = [getdate().year]
	return "\n".join(str(year) for year in year_list)


def mark_holidays(att_map, from_date, to_date, students_list):
	holiday_list = get_holiday_list()
	holidays = get_holidays(holiday_list)

	for dt in daterange(getdate(from_date), getdate(to_date)):
		if dt in holidays:
			for student in students_list:
				att_map.setdefault(student, frappe._dict()).setdefault(dt, "Holiday")

	return att_map
