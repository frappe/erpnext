# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt, getdate, nowdate

from erpnext.controllers.mapper import get_qty_already_mapped


@frappe.whitelist()
def make_purchase_order(
	source_name: str, target_doc: str | dict | Document | None = None, args: str | dict | None = None
):
	supplier_quotation = frappe.db.get_value(
		"Supplier Quotation",
		source_name,
		["transaction_date", "valid_till", "has_unit_price_items"],
		as_dict=True,
	)
	if supplier_quotation.valid_till and (
		supplier_quotation.valid_till < supplier_quotation.transaction_date
		or supplier_quotation.valid_till < getdate(nowdate())
	):
		frappe.throw(_("Validity period of this supplier quotation has ended."))

	if args is None:
		args = {}
	args = frappe.parse_json(args)
	ordered_items = get_ordered_items(source_name)

	mapped_items = get_qty_already_mapped(target_doc, "supplier_quotation_item")

	def set_missing_values(source, target):
		target.run_method("set_missing_values")
		target.run_method("get_schedule_dates")
		target.run_method("calculate_taxes_and_totals")

	def update_item(obj, target, source_parent):
		balance_stock_qty = obj.stock_qty - ordered_items.get(obj.name, 0.0)
		target.stock_qty = balance_stock_qty if balance_stock_qty > 0 else 0
		target.qty = flt(target.stock_qty) / flt(obj.conversion_factor)

	def can_map_row(item):
		return item.stock_qty > ordered_items.get(item.name, 0.0) or (
			supplier_quotation.has_unit_price_items and item.qty == 0
		)

	def select_item(d):
		filtered_items = args.get("filtered_children", [])
		child_filter = d.name in filtered_items if filtered_items else True
		return child_filter

	doclist = get_mapped_doc(
		"Supplier Quotation",
		source_name,
		{
			"Supplier Quotation": {
				"doctype": "Purchase Order",
				"field_no_map": ["transaction_date"],
				"validation": {
					"docstatus": ["=", 1],
				},
			},
			"Supplier Quotation Item": {
				"doctype": "Purchase Order Item",
				"field_map": [
					["name", "supplier_quotation_item"],
					["parent", "supplier_quotation"],
					["material_request", "material_request"],
					["material_request_item", "material_request_item"],
					["sales_order", "sales_order"],
				],
				"postprocess": update_item,
				"condition": lambda item: item.name not in mapped_items
				and can_map_row(item)
				and select_item(item),
			},
			"Purchase Taxes and Charges": {
				"doctype": "Purchase Taxes and Charges",
			},
		},
		target_doc,
		set_missing_values,
	)

	return doclist


@frappe.whitelist()
def make_purchase_invoice(source_name: str, target_doc: str | dict | Document | None = None):
	doc = get_mapped_doc(
		"Supplier Quotation",
		source_name,
		{
			"Supplier Quotation": {
				"doctype": "Purchase Invoice",
				"validation": {
					"docstatus": ["=", 1],
				},
			},
			"Supplier Quotation Item": {"doctype": "Purchase Invoice Item"},
			"Purchase Taxes and Charges": {"doctype": "Purchase Taxes and Charges"},
		},
		target_doc,
	)

	return doc


@frappe.whitelist()
def make_quotation(source_name: str, target_doc: str | dict | Document | None = None):
	doclist = get_mapped_doc(
		"Supplier Quotation",
		source_name,
		{
			"Supplier Quotation": {
				"doctype": "Quotation",
				"field_map": {
					"name": "supplier_quotation",
				},
			},
			"Supplier Quotation Item": {
				"doctype": "Quotation Item",
				"condition": lambda doc: frappe.db.get_value("Item", doc.item_code, "is_sales_item") == 1,
				"add_if_empty": True,
			},
		},
		target_doc,
	)

	return doclist


def get_ordered_items(supplier_quotation: str) -> frappe._dict:
	return frappe._dict(
		frappe.get_all(
			"Supplier Quotation Item",
			{"docstatus": 1, "parent": supplier_quotation, "ordered_qty": (">", 0)},
			["name", "ordered_qty"],
			as_list=True,
		)
	)
