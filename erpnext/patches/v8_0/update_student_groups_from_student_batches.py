# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.utils.rename_field import *
from frappe.model.mapper import get_mapped_doc


def execute():
	if frappe.db.table_exists("Student Batch"):
		student_batches = frappe.db.sql('''select name as student_group_name, student_batch_name as batch,
			program, academic_year, academic_term from `tabStudent Batch`''', as_dict=1)

		for student_batch in student_batches:
			if frappe.db.exists("Student Group", student_batch.get("student_group_name")):
				student_group = frappe.get_doc("Student Group", student_batch.get("student_group_name"))

				if frappe.db.table_exists("Student Batch Student"):
					current_student_list = frappe.db.sql('''select student from `tabStudent Group Student`
						where parent=%s''', (student_group.name), as_list=1)
					current_student_list = [d for student in current_student_list for d in student]

					student_list = frappe.db.sql('''select student, student_name from `tabStudent Batch Student`
						where student not in (%s) and parent=%s''' % (", ".join(['%s']*len(current_student_list)), "%s"),
						tuple(current_student_list + [student_group.name]), as_dict=1)

					if student_list:
						student_group.extend("students", student_list)

				if frappe.db.table_exists("Student Batch Instructor"):
					current_instructor_list = frappe.db.sql('''select instructor from `tabStudent Batch Instructor`
						where parent=%s''', (student_group.name), as_list=1)
					current_instructor_list = [d for instructor in current_instructor_list for d in instructor]
					current_instructor_list = [" " if not current_instructor_list else current_instructor_list]

					instructor_list = frappe.db.sql('''select instructor, instructor_name from `tabStudent Batch Instructor`
						where instructor not in (%s) and parent=%s''' % (", ".join(['%s']*len(current_instructor_list)), "%s"),
						tuple(current_instructor_list + [student_group.name]), as_dict=1)

					if instructor_list:
						student_group.extend("instructors", instructor_list)

				student_group.save()
