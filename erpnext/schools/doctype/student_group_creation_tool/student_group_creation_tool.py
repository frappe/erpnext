# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from erpnext.schools.doctype.student_group.student_group import get_students

class StudentGroupCreationTool(Document):
	def get_courses(self):
		group_list = []

		batches = frappe.db.sql('''select name as batch from `tabStudent Batch Name`''', as_dict=1)
		for batch in batches:
			group_list.append({"group_based_on":"Batch", "batch":batch.batch})

		courses = frappe.db.sql('''select course, course_name from `tabProgram Course` where parent=%s''',
			(self.program), as_dict=1)
		if self.separate_groups:
			from itertools import product
			course_list = product(courses,batches)
			for course in course_list:
				temp_dict = {}
				temp_dict.update({"group_based_on":"Course"})
				temp_dict.update(course[0])
				temp_dict.update(course[1])
				group_list.append(temp_dict)
		else:
			for course in courses:
				course.update({"group_based_on":"Course"})
				group_list.append(course)

		for group in group_list:
			if group.get("group_based_on") == "Batch":
				student_group_name = self.program + "/" + group.get("batch") + "/" + (self.academic_term if self.academic_term else self.academic_year)
				group.update({"student_group_name": student_group_name})
			elif group.get("group_based_on") == "Course":
				student_group_name = group.get("course") + "/" + self.program + ("/" + group.get("batch") if group.get("batch") else "") + "/" + (self.academic_term if self.academic_term else self.academic_year)
				group.update({"student_group_name": student_group_name})

		return group_list

	def create_student_groups(self):
		if not self.courses:
			frappe.throw(_("""No Student Groups created."""))

		l = len(self.courses)
		for d in self.courses:
			if not d.student_group_name:
				frappe.throw(_("""Student Group Name is mandatory in row {0}""".format(d.idx)))

			if d.group_based_on == "Course" and not d.course:
				frappe.throw(_("""Course is mandatory in row {0}""".format(d.idx)))

			if d.group_based_on == "Batch" and not d.batch:
				frappe.throw(_("""Batch is mandatory in row {0}""".format(d.idx)))

			frappe.publish_realtime('student_group_creation_progress', {"progress": [d.idx, l]}, user=frappe.session.user)

			student_group = frappe.new_doc("Student Group")
			student_group.student_group_name = d.student_group_name
			student_group.group_based_on = d.group_based_on
			student_group.program = self.program
			student_group.course = d.course
			student_group.batch = d.batch
			student_group.max_strength = d.max_strength
			student_group.academic_term = self.academic_term
			student_group.academic_year = self.academic_year
			student_list = get_students(self.academic_year, d.group_based_on, self.academic_term, self.program, d.batch, d.course)

			for student in student_list:
				student_group.append('students', student)
			student_group.save()

		frappe.msgprint(_("{0} Student Groups created.".format(l)))