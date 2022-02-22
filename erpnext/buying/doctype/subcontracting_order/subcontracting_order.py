# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc


class SubcontractingOrder(Document):
	pass


@frappe.whitelist()
def make_subcontracting_receipt(source_name, target_doc=None):
	return get_mapped_subcontracting_receipt(source_name, target_doc)

def get_mapped_subcontracting_receipt(source_name, target_doc=None, ignore_permissions=False):
	fields = {
		"Subcontracting Order": {
			"doctype": "Subcontracting Receipt",
			"validation": {
				"docstatus": ["=", 1],
			}
		},
		"Subcontracting Order Item": {
			"doctype": "Subcontracting Receipt Item",
		},
	}

	doc = get_mapped_doc("Subcontracting Order", source_name, fields)
	return doc