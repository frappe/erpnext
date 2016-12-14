# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe.model.document import Document
from erpnext.schools.api import get_grade

class AssessmentResult(Document):
	def validate(self):
		self.maximum_score = frappe.db.get_value("Assessment", self.assessment, "maximum_assessment_score")
		self.validate_grade()
	
	def validate_grade(self):
		self.total_score = 0.0
		for d in self.details:
			if d.score > d.maximum_score:
				frappe.throw(_("Score cannot be greater than Maximum Score"))
			else:
				d.grade = get_grade(self.grading_scale, (flt(d.score)/d.maximum_score)*100)
				self.total_score += d.score
		self.grade = get_grade(self.grading_scale, (self.total_score/self.maximum_score)*100)
	