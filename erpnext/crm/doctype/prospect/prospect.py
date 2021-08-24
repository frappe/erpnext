# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc

class Prospect(Document):
	pass

@frappe.whitelist()
def make_customer(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.customer_type = "Company"
		target.company_name = source.name
		target.customer_group = source.customer_group or frappe.db.get_default("Customer Group")

	doclist = get_mapped_doc("Prospect", source_name,
		{"Prospect": {
			"doctype": "Customer",
			"field_map": {
				"company_name": "customer_name",
				"currency": "default_currency",
				"fax": "fax"
			}
		}}, target_doc, set_missing_values, ignore_permissions=False)

	return doclist

@frappe.whitelist()
def make_opportunity(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.opportunity_from = "Prospect"
		target.customer_name = source.company_name
		target.customer_group = source.customer_group or frappe.db.get_default("Customer Group")

	doclist = get_mapped_doc("Prospect", source_name,
		{"Prospect": {
			"doctype": "Opportunity",
			"field_map": {
				"name": "party_name",
			}
		}}, target_doc, set_missing_values, ignore_permissions=False)

	return doclist
