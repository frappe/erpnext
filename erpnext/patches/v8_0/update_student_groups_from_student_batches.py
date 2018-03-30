# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.utils.rename_field import *
from frappe.model.mapper import get_mapped_doc


def execute():
	if frappe.db.table_exists("Student Batch"):
		student_batches = frappe.db.sql('''select name from `tabStudent Batch`''', as_dict=1)

		for student_batch in student_batches:
			if frappe.db.exists("Student Group", student_batch.get("name")):
				student_group = frappe.get_doc("Student Group", student_batch.get("name"))

				if frappe.db.table_exists("Student Batch Student"):
					current_student_list = frappe.db.sql_list('''select student from `tabStudent Group Student`
						where parent=%s''', (student_group.name))
					batch_student_list = frappe.db.sql_list('''select student from `tabStudent Batch Student`
						where parent=%s''', (student_group.name))

					student_list = list(set(batch_student_list)-set(current_student_list))
					if student_list:
						student_group.extend("students", [{"student":d} for d in student_list])

				if frappe.db.table_exists("Student Batch Instructor"):
					current_instructor_list = frappe.db.sql_list('''select instructor from `tabStudent Group Instructor`
						where parent=%s''', (student_group.name))
					batch_instructor_list = frappe.db.sql_list('''select instructor from `tabStudent Batch Instructor`
						where parent=%s''', (student_group.name))

					instructor_list = list(set(batch_instructor_list)-set(current_instructor_list))
					if instructor_list:
						student_group.extend("instructors", [{"instructor":d} for d in instructor_list])

				student_group.save()
