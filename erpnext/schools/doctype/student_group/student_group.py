# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from erpnext.schools.utils import validate_duplicate_student

class StudentGroup(Document):
	def autoname(self):
		self.name = frappe.db.get_value("Course", self.course, "course_abbreviation")
		if not self.name:
			self.name = self.course
		if self.student_batch:
			self.name += "-" + self.student_batch
		else:
			prog_abb = frappe.db.get_value("Program", self.program, "program_abbreviation")
			if not prog_abb:
				prog_abb = self.program
			if prog_abb:
				self.name += "-" + prog_abb
			if self.academic_year:
				self.name += "-" + self.academic_year
		if self.academic_term:
			self.name += "-" + self.academic_term
	
	def validate(self):
		self.validate_strength()
		self.validate_student_name()
		validate_duplicate_student(self.students)

	def validate_strength(self):
		if self.max_strength and len(self.students) > self.max_strength:
			frappe.throw(_("""Cannot enroll more than {0} students for this student group.""").format(self.max_strength))

	def validate_student_name(self):
		for d in self.students:
			d.student_name = frappe.db.get_value("Student", d.student, "title")
	
	