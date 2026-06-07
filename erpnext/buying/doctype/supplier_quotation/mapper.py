# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt


@frappe.whitelist()
def make_purchase_order(
	source_name: str, target_doc: str | Document | None = None, args: str | dict | None = None
):
	if args is None:
		args = {}
	if isinstance(args, str):
		args = json.loads(args)

	def set_missing_values(source, target):
		target.run_method("set_missing_values")
		target.run_method("get_schedule_dates")
		target.run_method("calculate_taxes_and_totals")

	def update_item(obj, target, source_parent):
		target.stock_qty = flt(obj.qty) * flt(obj.conversion_factor)

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
				"condition": select_item,
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
def make_purchase_invoice(source_name: str, target_doc: str | Document | None = None):
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
def make_quotation(source_name: str, target_doc: str | Document | None = None):
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
