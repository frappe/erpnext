# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.utils.rename_field import *
from frappe.model.mapper import get_mapped_doc


def execute():

	# for converting student batch into student group
	frappe.reload_doctype("Student Group")
	student_batches = frappe.db.sql('''select name as student_group_name, student_batch_name as batch, program, academic_year, academic_term
		from `tabStudent Batch`''', as_dict=1)
	for student_batch in student_batches:
		student_batch.update({"doctype":"Student Group", "group_based_on": "Batch"})
		doc = frappe.get_doc(student_batch)
		doc.save()
		student_list = frappe.db.sql('''select student, student_name, active from `tabStudent Batch Student` where parent=%s''', (doc.name), as_dict=1)
		if student_list:
			doc.extend("students", student_list)

		instructor_list = frappe.db.sql('''select instructor, instructor_name from `tabStudent Batch Instructor` where parent=%s''', (doc.name), as_dict=1)
		if instructor_list:
			doc.extend("instructors", instructor_list)
		doc.save()

	# delete the student batch and child-table
	frappe.delete_doc("DocType", "Student Batch", force=1)
	# frappe.db.sql("drop table if exists `tabStudent Batch`")
	frappe.delete_doc("DocType", "Student Batch Student", force=1)
	# frappe.db.sql("drop table if exists `tabStudent Batch Student`")
	frappe.delete_doc("DocType", "Student Batch Instructor", force=1)
	# frappe.db.sql("drop table if exists `tabStudent Batch Instructor`")

	# delete the student batch creation tool
	frappe.delete_doc("DocType", "Student Batch Creation Tool", force=1)
	# frappe.db.sql("drop table if exists `tabStudent Batch Creation Tool`")

	# delete the student batch creation tool
	frappe.delete_doc("DocType", "Attendance Tool Student", force=1)
	# frappe.db.sql("drop table if exists `tabAttendance Tool Student`")

	# change the student batch to student group in the student attendance
	frappe.reload_doctype("Student Attendance")

	table_columns = frappe.db.get_table_columns("Student Attendance")
	if "student_batch" in table_columns:
		rename_field("Student Attendance", "student_batch", "student_group")
