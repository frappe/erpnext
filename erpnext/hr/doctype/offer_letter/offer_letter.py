# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc

class OfferLetter(Document):
	pass

@frappe.whitelist()
def make_employee(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.personal_email = frappe.db.get_value("Job Applicant", source.job_applicant, "email_id")
	doc = get_mapped_doc("Offer Letter", source_name, {
			"Offer Letter": {
				"doctype": "Employee",
				"field_map": {
					"applicant_name": "employee_name",
				}}
		}, target_doc, set_missing_values)
	return doc

