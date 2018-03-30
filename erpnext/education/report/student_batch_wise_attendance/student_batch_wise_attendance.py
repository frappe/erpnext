# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, cint, getdate
from frappe import msgprint, _

def execute(filters=None):
	if not filters: filters = {}

	if not filters.get("date"):
		msgprint(_("Please select date"), raise_exception=1)
	
	columns = get_columns(filters)

	active_student_group = get_active_student_group()

	data = []
	for student_group in active_student_group:
		row = [student_group.name]
		present_students = 0
		absent_students = 0
		student_group_strength = get_student_group_strength(student_group.name)
		student_attendance = get_student_attendance(student_group.name, filters.get("date"))
		if student_attendance:
			for attendance in student_attendance:
				if attendance.status== "Present":
					present_students = attendance.count
				elif attendance.status== "Absent":
					absent_students = attendance.count

		unmarked_students = student_group_strength - (present_students + absent_students)
		row+= [student_group_strength, present_students, absent_students, unmarked_students]
		data.append(row)

	return columns, data

def get_columns(filters):
	columns = [ 
		_("Student Group") + ":Link/Student Group:250", 
		_("Student Group Strength") + "::170", 
		_("Present") + "::90", 
		_("Absent") + "::90",
		_("Not Marked") + "::90"
	]
	return columns

def get_active_student_group():
	active_student_groups = frappe.db.sql("""select name from `tabStudent Group` where group_based_on = "Batch" 
		and academic_year=%s order by name""", (frappe.defaults.get_defaults().academic_year), as_dict=1)
	return active_student_groups

def get_student_group_strength(student_group):
	student_group_strength = frappe.db.sql("""select count(*) from `tabStudent Group Student` 
		where parent = %s and active=1""", student_group)[0][0]
	return student_group_strength

def get_student_attendance(student_group, date):
	student_attendance = frappe.db.sql("""select count(*) as count, status from `tabStudent Attendance` where \
				student_group= %s and date= %s and\
				(course_schedule is Null or course_schedule='') group by status""",
				(student_group, date), as_dict=1)
	return student_attendance