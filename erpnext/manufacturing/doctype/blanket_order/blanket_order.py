# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt, getdate

from erpnext.stock.doctype.item.item import get_item_defaults


class BlanketOrder(Document):
	def validate(self):
		self.validate_dates()
		self.validate_duplicate_items()

	def validate_dates(self):
		if getdate(self.from_date) > getdate(self.to_date):
			frappe.throw(_("From date cannot be greater than To date"))

	def validate_duplicate_items(self):
		item_list = []
		for item in self.items:
			if item.item_code in item_list:
				frappe.throw(_("Note: Item {0} added multiple times").format(frappe.bold(item.item_code)))
			item_list.append(item.item_code)

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
def make_order(source_name):
	doctype = frappe.flags.args.doctype

	def update_doc(source_doc, target_doc, source_parent):
		if doctype == 'Quotation':
			target_doc.quotation_to = 'Customer'
			target_doc.party_name = source_doc.customer

	def update_item(source, target, source_parent):
		target_qty = source.get("qty") - source.get("ordered_qty")
		target.qty = target_qty if not flt(target_qty) < 0 else 0
		item = get_item_defaults(target.item_code, source_parent.company)
		if item:
			target.item_name = item.get("item_name")
			target.description = item.get("description")
			target.uom = item.get("stock_uom")
			target.against_blanket_order = 1
			target.blanket_order = source_name

	target_doc = get_mapped_doc("Blanket Order", source_name, {
		"Blanket Order": {
			"doctype": doctype,
			"postprocess": update_doc
		},
		"Blanket Order Item": {
			"doctype": doctype + " Item",
			"field_map": {
				"rate": "blanket_order_rate",
				"parent": "blanket_order"
			},
			"postprocess": update_item
		}
	})
	return target_doc
