# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc


class PatientAssessment(Document):
	def validate(self):
		self.set_total_score()

	def set_total_score(self):
		total_score = 0
		for entry in self.assessment_sheet:
			total_score += int(entry.score)
		self.total_score_obtained = total_score


@frappe.whitelist()
def create_patient_assessment(source_name, target_doc=None):
	doc = get_mapped_doc(
		"Therapy Session",
		source_name,
		{
			"Therapy Session": {
				"doctype": "Patient Assessment",
				"field_map": [
					["therapy_session", "name"],
					["patient", "patient"],
					["practitioner", "practitioner"],
				],
			}
		},
		target_doc,
	)

	return doc
