# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from erpnext.stock.doctype.item.item import get_item_defaults


class BlanketOrder(Document):
	pass


@frappe.whitelist()
def make_sales_order(source_name):
	def update_item(source, target, source_parent):
		item = get_item_defaults(target.item_code, source_parent.company)
		if item:
			target.item_name = item.get("item_name")
			target.description = item.get("description")
			target.uom = item.get("stock_uom")

	target_doc = get_mapped_doc("Blanket Order", source_name, {
		"Blanket Order": {
			"doctype": "Sales Order"
		},
		"Blanket Order Item": {
			"doctype": "Sales Order Item",
			"field_map": {
				"rate": "blanket_order_rate",
				"parent": "blanket_order"
			},
			"postprocess": update_item
		}
	})
	return target_doc

@frappe.whitelist()
def make_purchase_order(source_name):
	def update_item(source, target, source_parent):
		item = get_item_defaults(target.item_code, source_parent.company)
		if item:
			target.item_name = item.get("item_name")
			target.description = item.get("description")
			target.uom = item.get("stock_uom")
			target.warehouse = item.get("default_warehouse")

	target_doc = get_mapped_doc("Blanket Order", source_name, {
		"Blanket Order": {
			"doctype": "Purchase Order"
		},
		"Blanket Order Item": {
			"doctype": "Purchase Order Item",
			"field_map": {
				"rate": "blanket_order_rate",
				"parent": "blanket_order"
			},
			"postprocess": update_item
		}
	})
	return target_doc
