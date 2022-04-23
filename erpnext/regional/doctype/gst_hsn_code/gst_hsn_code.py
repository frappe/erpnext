# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class GSTHSNCode(Document):
	pass

@frappe.whitelist()
def update_taxes_in_item_master(taxes, hsn_code):
	items = frappe.get_list("Item", filters={
		'gst_hsn_code': hsn_code
	})

	taxes = frappe.parse_json(taxes)
	frappe.enqueue(update_item_document, items=items, taxes=taxes)
	return 1

def update_item_document(items, taxes):
	for item in items:
		item_to_be_updated=frappe.get_doc("Item", item.name)
		item_to_be_updated.taxes = []
		for tax in taxes:
			tax = frappe._dict(tax)
			item_to_be_updated.append("taxes", {
				'item_tax_template': tax.item_tax_template,
				'tax_category': tax.tax_category,
				'valid_from': tax.valid_from
			})
			item_to_be_updated.save()