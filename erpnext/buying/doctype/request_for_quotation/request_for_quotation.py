# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.mapper import get_mapped_doc
from erpnext.stock.doctype.material_request.material_request import set_missing_values
from frappe.model.document import Document

class RequestforQuotation(Document):
	pass
    
@frappe.whitelist()
def make_supplier_quotation(source_name, target_doc=None):
	def postprocess(source, target_doc):
		set_missing_values(source, target_doc)

	doclist = get_mapped_doc("Request for Quotation", source_name, {
		"Request for Quotation": {
			"doctype": "Supplier Quotation",
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Request for Quotation Item": {
			"doctype": "Supplier Quotation Item",
			"field_map": [
				["name", "request_for_quotation_item"],
				["parent", "request_for_quotation"],
				["uom", "uom"]
			],
		}
	}, target_doc, postprocess)

	return doclist
