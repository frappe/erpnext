# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, cint, getdate, get_first_day, get_last_day, date_diff, add_days
from frappe import msgprint, _
from calendar import monthrange
from erpnext.schools.api import get_student_batch_students

def execute(filters=None):
	if not filters: filters = {}

	from_date = get_first_day(filters["month"] + '-' + filters["year"])
	to_date = get_last_day(filters["month"] + '-' + filters["year"])
	total_days_in_month = date_diff(to_date, from_date) +1
	columns = get_columns(total_days_in_month)
	att_map = get_attendance_list(from_date, to_date, filters.get("student_batch"))
	students = get_student_batch_students(filters.get("student_batch"))
	data = []
	for stud in students:
		row = [stud.student, stud.student_name]
		date = from_date
		total_p = total_a = 0.0
		for day in range(total_days_in_month):
			status="None"
			if att_map.get(stud.student):
				status = att_map.get(stud.student).get(date, "None")
			status_map = {"Present": "P", "Absent": "A", "None": ""}
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
	columns = [ _("Student") + ":Link/Student:90", _("Student Name") + "::150"]
	for day in range(days_in_month):
		columns.append(cstr(day+1) +"::20")
	columns += [_("Total Present") + ":Int:95", _("Total Absent") + ":Int:90"]
	return columns

def get_attendance_list(from_date, to_date, student_batch):
	attendance_list = frappe.db.sql("""select student, date, status 
		from `tabStudent Attendance` where docstatus = 1 and student_batch = %s 
		and date between %s and %s
		order by student, date""",
		(student_batch, from_date, to_date), as_dict=1)
	att_map = {}
	for d in attendance_list:
		att_map.setdefault(d.student, frappe._dict()).setdefault(d.date, "")
		students_with_leave_application = get_students_with_leave_application(d.date)
		if students_with_leave_application:
			for stud in students_with_leave_application:
				if stud.student== d.student:
					att_map[d.student][d.date] = "Present"
					break
				else:		
					att_map[d.student][d.date] = d.status
		else:
			att_map[d.student][d.date] = d.status
	return att_map

def get_students_with_leave_application(date):
	students_with_leave_application = frappe.db.sql("""select student from 
		`tabStudent Leave Application` where mark_as_present and docstatus = 1 and 
		%s between from_date and to_date""", date, as_dict=1)	
	return students_with_leave_application

@frappe.whitelist()
def get_attendance_years():
	year_list = frappe.db.sql_list("""select distinct YEAR(date) from `tabStudent Attendance` ORDER BY YEAR(date) DESC""")
	if not year_list:
		year_list = [getdate().year]
	return "\n".join(str(year) for year in year_list)
