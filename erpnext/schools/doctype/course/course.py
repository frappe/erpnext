# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class Course(Document):
	def validate(self):
		self.validate_evaluation_criterias()
	
	def validate_evaluation_criterias(self):
		if self.evaluation_criterias:
			total_weightage = 0
			for criteria in self.evaluation_criterias:
				total_weightage += criteria.weightage
			if total_weightage != 100:
				frappe.throw(_("Total Weightage of all Evaluation Criterias must be 100%"))
