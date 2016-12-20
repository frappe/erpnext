# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, cint, getdate
from frappe import msgprint, _
from calendar import monthrange
from erpnext.schools.api import get_student_batch_students

def execute(filters=None):
	if not filters: filters = {}

	conditions, filters = get_conditions(filters)
	columns = get_columns(filters)
	att_map = get_attendance_list(conditions, filters)
	students = get_student_batch_students(filters.get("student_batch"))
	data = []
	for stud in students:
		row = [stud.student, stud.student_name]

		total_p = total_a = 0.0
		for day in range(filters["total_days_in_month"]):
			status="None"
			if att_map.get(stud.student):
				status = att_map.get(stud.student).get(day + 1, "None")
			status_map = {"Present": "P", "Absent": "A", "None": ""}
			row.append(status_map[status])

			if status == "Present":
				total_p += 1
			elif status == "Absent":
				total_a += 1

		row += [total_p, total_a]
		data.append(row)

	return columns, data

def get_columns(filters):
	columns = [ _("Student") + ":Link/Student:90", _("Student Name") + "::150"]

	for day in range(filters["total_days_in_month"]):
		columns.append(cstr(day+1) +"::20")

	columns += [_("Total Present") + ":Int:95", _("Total Absent") + ":Int:90"]
	return columns

def get_attendance_list(conditions, filters):
	attendance_list = frappe.db.sql("""select student, day(date) as day_of_month,
		status from `tabStudent Attendance` where docstatus = 1 %s order by student, date""" %
		conditions, filters, as_dict=1)

	students_with_leave_application = get_students_with_leave_application(filters)

	att_map = {}
	for d in attendance_list:
		att_map.setdefault(d.student, frappe._dict()).setdefault(d.day_of_month, "")
		for stud in students_with_leave_application:
			if stud.student== d.student and stud.day_of_month== d.day_of_month:
				att_map[d.student][d.day_of_month] = "Present"
				break
			else:		
				att_map[d.student][d.day_of_month] = d.status

	return att_map

def get_students_with_leave_application(filters):
	students_with_leave_application = frappe.db.sql("""select student, day(date) as day_of_month
		from `tabStudent Leave Application` where mark_as_present and docstatus = 1 
		and month(date) = %(month)s and year(date) = %(year)s
		order by student, date""", filters, as_dict=1)
	return students_with_leave_application 

def get_conditions(filters):
	if not (filters.get("month") and filters.get("year")):
		msgprint(_("Please select month and year"), raise_exception=1)
	
	filters["month"] = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov",
		"Dec"].index(filters.month) + 1

	filters["total_days_in_month"] = monthrange(cint(filters.year), filters.month)[1]
	
	conditions = " and month(date) = %(month)s and year(date) = %(year)s"

	if filters.get("student_batch"): conditions += " and student_batch = %(student_batch)s"
	
	return conditions, filters

@frappe.whitelist()
def get_attendance_years():
	year_list = frappe.db.sql_list("""select distinct YEAR(date) from `tabStudent Attendance` ORDER BY YEAR(date) DESC""")
	if not year_list:
		year_list = [getdate().year]

	return "\n".join(str(year) for year in year_list)
