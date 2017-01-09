# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
from frappe.model.document import Document
from erpnext.schools.api import get_grade
from erpnext.schools.api import get_assessment_details

class AssessmentResult(Document):
	def validate(self):
		self.grading_scale = frappe.db.get_value("Assessment Plan", self.assessment_plan, "grading_scale")
		self.validate_maximum_score()
		self.validate_grade()
	
	def validate_maximum_score(self):
		self.maximum_score = frappe.db.get_value("Assessment Plan", self.assessment_plan, "maximum_assessment_score")
		assessment_details = get_assessment_details(self.assessment_plan)
		max_scores = {}
		for d in assessment_details:
			max_scores.update({d.evaluation_criteria: d.maximum_score})

		for d in self.details:
			d.maximum_score = max_scores.get(d.evaluation_criteria)
			if d.score > d.maximum_score:
				frappe.throw(_("Score cannot be greater than Maximum Score"))
		
	def validate_grade(self):
		self.total_score = 0.0
		for d in self.details:
			d.grade = get_grade(self.grading_scale, (flt(d.score)/d.maximum_score)*100)
			self.total_score += d.score
		self.grade = get_grade(self.grading_scale, (self.total_score/self.maximum_score)*100)
