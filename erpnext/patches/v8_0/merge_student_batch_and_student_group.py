# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.utils.rename_field import *
from frappe.model.mapper import get_mapped_doc


def execute():
	# for converting student batch into student group
	for doctype in ["Student Group", "Student Group Student", 'Program Enrollment',
		"Student Group Instructor", "Student Attendance", "Student", "Student Batch Name"]:
		# 'Schools' module changed to the 'Education'
		# frappe.reload_doc("schools", "doctype", frappe.scrub(doctype))

		frappe.reload_doc("education", "doctype", frappe.scrub(doctype))

	if frappe.db.table_exists("Student Batch"):
		student_batches = frappe.db.sql('''select name as student_group_name, student_batch_name as batch,
			program, academic_year, academic_term from `tabStudent Batch`''', as_dict=1)

		for student_batch in student_batches:
			# create student batch name if does not exists !!
			if student_batch.get("batch") and not frappe.db.exists("Student Batch Name", student_batch.get("batch")):
				frappe.get_doc({
					"doctype": "Student Batch Name",
					"batch_name": student_batch.get("batch")
				}).insert(ignore_permissions=True)

			student_batch.update({"doctype":"Student Group", "group_based_on": "Batch"})
			doc = frappe.get_doc(student_batch)

			if frappe.db.sql("SHOW COLUMNS FROM `tabStudent Batch Student` LIKE 'active'"):
				cond = ", active"
			else:
				cond = " "
			student_list = frappe.db.sql('''select student, student_name {cond} from `tabStudent Batch Student`
				where parent=%s'''.format(cond=cond), (doc.student_group_name), as_dict=1)

			if student_list:
				for i, student in enumerate(student_list):
					student.update({"group_roll_number": i+1})
				doc.extend("students", student_list)

			instructor_list = None
			if frappe.db.table_exists("Student Batch Instructor"):
				instructor_list = frappe.db.sql('''select instructor, instructor_name from `tabStudent Batch Instructor`
					where parent=%s''', (doc.student_group_name), as_dict=1)
			if instructor_list:
				doc.extend("instructors", instructor_list)
			doc.save()

	# delete the student batch and child-table
	if frappe.db.table_exists("Student Batch"):
		frappe.delete_doc("DocType", "Student Batch", force=1)
	if frappe.db.table_exists("Student Batch Student"):
		frappe.delete_doc("DocType", "Student Batch Student", force=1)
	if frappe.db.table_exists("Student Batch Instructor"):
		frappe.delete_doc("DocType", "Student Batch Instructor", force=1)

	# delete the student batch creation tool
	if frappe.db.table_exists("Student Batch Creation Tool"):
		frappe.delete_doc("DocType", "Student Batch Creation Tool", force=1)

	# delete the student batch creation tool
	if frappe.db.table_exists("Attendance Tool Student"):
		frappe.delete_doc("DocType", "Attendance Tool Student", force=1)

	# change the student batch to student group in the student attendance
	table_columns = frappe.db.get_table_columns("Student Attendance")
	if "student_batch" in table_columns:
		rename_field("Student Attendance", "student_batch", "student_group")
