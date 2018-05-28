# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc


class BlanketOrder(Document):
	pass


@frappe.whitelist()
def make_sales_order(source_name):
	return get_mapped_doc("Blanket Order", source_name, {
		"Blanket Order": {
			"doctype": "Sales Order"
		},
		"Blanket Order Item": {
			"doctype": "Sales Order Item",
			"field_map": {
				"rate": "blanket_order_rate",
				"parent": "blanket_order"
			}
		}
	})

@frappe.whitelist()
def make_purchase_order(source_name):
	return get_mapped_doc("Blanket Order", source_name, {
		"Blanket Order": {
			"doctype": "Purchase Order"
		},
		"Blanket Order Item": {
			"doctype": "Purchase Order Item",
			"field_map": {
				"rate": "blanket_order_rate",
				"parent": "blanket_order"
			}
		}
	})
