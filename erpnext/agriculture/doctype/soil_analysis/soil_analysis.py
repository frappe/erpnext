# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class SoilAnalysis(Document):
	@frappe.whitelist()
	def load_contents(self):
		docs = frappe.get_all("Agriculture Analysis Criteria", filters={'linked_doctype':'Soil Analysis'})
		for doc in docs:
			self.append('soil_analysis_criteria', {'title': str(doc.name)})