# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class Course(Document):
	def validate(self):
		self.validate_assessment_criteria()
	
	def validate_assessment_criteria(self):
		if self.assessment_criteria:
			total_weightage = 0
			for criteria in self.assessment_criteria:
				total_weightage += criteria.weightage
			if total_weightage != 100:
				frappe.throw(_("Total Weightage of all Assessment Criteria must be 100%"))
