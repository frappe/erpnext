# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document


class WaterAnalysis(Document):
	@frappe.whitelist()
	def load_contents(self):
		docs = frappe.get_all(
			"Agriculture Analysis Criteria", filters={"linked_doctype": "Water Analysis"}
		)
		for doc in docs:
			self.append("water_analysis_criteria", {"title": str(doc.name)})

	@frappe.whitelist()
	def update_lab_result_date(self):
		if not self.result_datetime:
			self.result_datetime = self.laboratory_testing_datetime

	def validate(self):
		if self.collection_datetime > self.laboratory_testing_datetime:
			frappe.throw(_("Lab testing datetime cannot be before collection datetime"))
		if self.laboratory_testing_datetime > self.result_datetime:
			frappe.throw(_("Lab result datetime cannot be before testing datetime"))
