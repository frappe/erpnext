# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from erpnext.stock.doctype.material_request.material_request import set_missing_values
from frappe.model.document import Document

class RequestforQuotation(Document):
	def validate(self):
		self.validate_duplicate_supplier()
		
	def validate_duplicate_supplier(self):
		supplier_list = [d.supplier for d in self.suppliers]
		if len(supplier_list) != len(set(supplier_list)):
			frappe.throw(_("Same supplier has been entered multiple times"))
	
@frappe.whitelist()
def get_supplier(doctype, txt, searchfield, start, page_len, filters):
	query = """	Select supplier from `tabRFQ Supplier` where parent = '{parent}' and supplier like %s
				limit {start}, {page_len} """
				
	return frappe.db.sql(query.format(parent=filters.get('parent'), start=start, page_len=page_len), '%{0}%'.format(txt))
    
@frappe.whitelist()
def make_supplier_quotation(source_name, for_supplier, target_doc=None):
	def postprocess(source, target_doc):
		target_doc.supplier = for_supplier
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
