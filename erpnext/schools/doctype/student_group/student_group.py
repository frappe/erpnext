# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from erpnext.schools.utils import validate_duplicate_student
from erpnext.schools.api import get_student_batch_students

class StudentGroup(Document):
	def validate(self):
		self.validate_mandatory_fields()
		self.validate_strength()
		self.validate_students()
		validate_duplicate_student(self.students)

	def validate_mandatory_fields(self):
		if self.group_based_on == "Course" and not self.course:
			frappe.throw(_("Please select Course"))
		elif self.group_based_on == "Batch" and (not self.program or not self.batch):
			frappe.throw(_("Please select Program and Batch"))

	def validate_strength(self):
		if self.max_strength and len(self.students) > self.max_strength:
			frappe.throw(_("""Cannot enroll more than {0} students for this student group.""").format(self.max_strength))

	def validate_students(self):
		program_enrollment = self.get_program_enrollment()
		students = [d.student for d in program_enrollment] if program_enrollment else None
		for d in self.students:
			if d.student not in students:
				frappe.throw(_("{0} - {1} is not enrolled in the given {2}".format(d.student, d.student_name, self.group_based_on)))
			if not frappe.db.get_value("Student", d.student, "enabled") and d.active:
				d.active = 0
				frappe.throw(_("{0} - {1} is inactive student".format(d.student, d.student_name)))


	def update_students(self):
		enrolled_students = self.get_program_enrollment()
		group_student_list = [student.student for student in self.students]

		if enrolled_students:
			student_list = [];
			for s in enrolled_students:
				if s.student not in group_student_list:
					student_list.append(s.update({"active": 1}) if frappe.db.get_value("Student", s.student, "enabled")
						else s.update({"active": 0}))
			return student_list
		elif self.group_based_on != "Activity":
			frappe.throw(_("No students are enrolled in the given {}".format(self.group_based_on)))
		else:
			frappe.throw(_("Select students manually for the Activity based Group"))

	def get_program_enrollment(self):
		if self.group_based_on == "Batch":
			return frappe.db.sql('''select student, student_name from `tabProgram Enrollment` where academic_year = %s
				and program = %s and student_batch_name = %s order by student_name asc''',(self.academic_year, self.program, self.batch), as_dict=1)

		elif self.group_based_on == "Course":
			return frappe.db.sql('''
				select 
					pe.student, pe.student_name 
				from 
					`tabProgram Enrollment` pe, `tabProgram Enrollment Course` pec
				where
					pe.name = pec.parent and pec.course = %s
				order by
					pe.student_name asc
				''', (self.course), as_dict=1)
		else:
			return
