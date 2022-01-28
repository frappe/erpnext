# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document


class PlantAnalysis(Document):
	@frappe.whitelist()
	def load_contents(self):
		docs = frappe.get_all("Agriculture Analysis Criteria", filters={'linked_doctype':'Plant Analysis'})
		for doc in docs:
			self.append('plant_analysis_criteria', {'title': str(doc.name)})
