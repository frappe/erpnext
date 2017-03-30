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

	active_student_batch = get_active_student_batch()

	data = []
	for student_batch in active_student_batch:
		row = [student_batch.name]
		present_students = 0
		absent_students = 0
		student_batch_strength = get_student_batch_strength(student_batch.name)
		student_attendance = get_student_attendance(student_batch.name, filters.get("date"))
		if student_attendance:
			for attendance in student_attendance:
				if attendance.status== "Present":
					present_students = attendance.count
				elif attendance.status== "Absent":
					absent_students = attendance.count

		unmarked_students = student_batch_strength - (present_students + absent_students)
		row+= [student_batch_strength, present_students, absent_students, unmarked_students]
		data.append(row)

	return columns, data

def get_columns(filters):
	columns = [ 
		_("Student batch") + ":Link/Student Batch:250", 
		_("Student batch Strength") + "::170", 
		_("Present") + "::90", 
		_("Absent") + "::90",
		_("Not Marked") + "::90"
	]
	return columns

def get_active_student_batch():
	active_student_batch = frappe.db.sql("""select name from `tabStudent Batch` 
		where enabled = 1 order by name""", as_dict=1)
	return active_student_batch

def get_student_batch_strength(student_batch):
	student_batch_strength = frappe.db.sql("""select count(*) from `tabStudent Batch Student` 
		where parent = %s and active=1""", student_batch)[0][0]
	return student_batch_strength

def get_student_attendance(student_batch, date):
	student_attendance = frappe.db.sql("""select count(*) as count, status from `tabStudent Attendance` where \
				student_batch= %s and date= %s and\
				(course_schedule is Null or course_schedule='') group by status""",
				(student_batch, date), as_dict=1)
	return student_attendance