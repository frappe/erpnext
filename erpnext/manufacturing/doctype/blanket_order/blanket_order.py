# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate
from erpnext.stock.get_item_details import get_default_warehouse
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc


class BlanketOrder(Document):
	def validate(self):
		self.validate_dates()

	def validate_dates(self):
		if getdate(self.from_date) > getdate(self.to_date):
			frappe.throw(_("From date cannot be greater than To date")) 

	def update_ordered_qty(self):
		ref_doctype = "Sales Order" if self.blanket_order_type == "Selling" else "Purchase Order"
		item_ordered_qty = frappe._dict(frappe.db.sql("""
			select trans_item.item_code, sum(trans_item.stock_qty) as qty
			from `tab{0} Item` trans_item, `tab{0}` trans
			where trans.name = trans_item.parent
				and trans_item.blanket_order=%s
				and trans.docstatus=1
				and trans.status not in ('Closed', 'Stopped')
			group by trans_item.item_code
		""".format(ref_doctype), self.name))

		for d in self.items:
			d.db_set("ordered_qty", item_ordered_qty.get(d.item_code, 0))

@frappe.whitelist()
def make_sales_order(source_name):
	def update_item(source, target, source_parent, target_parent):
		target_qty = source.get("qty") - source.get("ordered_qty")
		target.qty = target_qty if not flt(target_qty) < 0 else 0
		item = frappe.get_cached_doc("Item", target.item_code) if target.item_code else None
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
	def update_item(source, target, source_parent, target_parent):
		target_qty = source.get("qty") - source.get("ordered_qty")
		target.qty = target_qty if not flt(target_qty) < 0 else 0
		item = frappe.get_cached_doc("Item", target.item_code) if target.item_code else None
		if item:
			target.item_name = item.get("item_name")
			target.description = item.get("description")
			target.uom = item.get("stock_uom")
			target.warehouse = get_default_warehouse(item, {'company': source_parent.company}, True)

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