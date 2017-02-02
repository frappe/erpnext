# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
import frappe
from frappe import _

class AssessmentPlan(Document):
	def validate(self):
		if not (self.student_batch or self.student_group):
			frappe.throw(_("Please select Student Group or Student Batch"))
		self.validate_student_batch()
		self.validate_overlap()
		self.validate_max_score()

	def validate_overlap(self):
		"""Validates overlap for Student Group/Student Batch, Instructor, Room"""
		
		from erpnext.schools.utils import validate_overlap_for

		#Validate overlapping course schedules.
		if self.student_batch:
			validate_overlap_for(self, "Course Schedule", "student_batch")

		if self.student_group:
			validate_overlap_for(self, "Course Schedule", "student_group")
		
		validate_overlap_for(self, "Course Schedule", "instructor")
		validate_overlap_for(self, "Course Schedule", "room")

		#validate overlapping assessment schedules.
		if self.student_batch:
			validate_overlap_for(self, "Assessment Plan", "student_batch")
		
		if self.student_group:
			validate_overlap_for(self, "Assessment Plan", "student_group")
		
		validate_overlap_for(self, "Assessment Plan", "room")
		validate_overlap_for(self, "Assessment Plan", "supervisor", self.supervisor)

	def validate_student_batch(self):
		if self.student_group:
			self.student_batch = frappe.db.get_value("Student Group", self.student_group, "student_batch")

	def validate_max_score(self):
		max_score = 0
		for d in self.assessment_criteria:
			max_score += d.maximum_score
		if self.maximum_assessment_score != max_score:
			frappe.throw(_("Sum of Scores of Assessment Criteria needs to be {0}.".format(self.maximum_assessment_score)))