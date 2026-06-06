# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt

from erpnext.controllers.accounts_controller import merge_taxes


@frappe.whitelist()
def make_debit_note(source_name: str, target_doc: str | Document | None = None):
	from erpnext.controllers.sales_and_purchase_return import make_return_doc

	return make_return_doc("Purchase Invoice", source_name, target_doc)


@frappe.whitelist()
def make_stock_entry(source_name: str, target_doc: str | Document | None = None):
	doc = get_mapped_doc(
		"Purchase Invoice",
		source_name,
		{
			"Purchase Invoice": {"doctype": "Stock Entry", "validation": {"docstatus": ["=", 1]}},
			"Purchase Invoice Item": {
				"doctype": "Stock Entry Detail",
				"field_map": {"stock_qty": "transfer_qty", "batch_no": "batch_no"},
			},
		},
		target_doc,
	)

	return doc


@frappe.whitelist()
def make_inter_company_sales_invoice(source_name: str, target_doc: Document | None = None):
	from erpnext.accounts.doctype.sales_invoice.mapper import make_inter_company_transaction

	return make_inter_company_transaction("Purchase Invoice", source_name, target_doc)


@frappe.whitelist()
def make_purchase_receipt(
	source_name: str, target_doc: str | Document | None = None, args: str | dict | None = None
):
	if args is None:
		args = {}
	if isinstance(args, str):
		args = json.loads(args)

	def post_parent_process(source_parent, target_parent):
		remove_items_with_zero_qty(target_parent)
		set_missing_values(source_parent, target_parent)

	def remove_items_with_zero_qty(target_parent):
		target_parent.items = [row for row in target_parent.get("items") if row.get("qty") != 0]

	def set_missing_values(source_parent, target_parent):
		target_parent.run_method("set_missing_values")
		if args and args.get("merge_taxes"):
			merge_taxes(source_parent, target_parent)
		target_parent.run_method("calculate_taxes_and_totals")

	def update_item(obj, target, source_parent):
		from erpnext.controllers.sales_and_purchase_return import get_returned_qty_map_for_row

		returned_qty_map = (
			get_returned_qty_map_for_row(
				source_parent.name, source_parent.supplier, obj.name, "Purchase Invoice"
			)
			or {}
		)

		target.qty = flt(obj.qty) - flt(obj.received_qty) - flt(returned_qty_map.get("qty"))
		target.received_qty = flt(obj.qty) - flt(obj.received_qty)
		target.stock_qty = (flt(obj.qty) - flt(obj.received_qty) - flt(returned_qty_map.get("qty"))) * flt(
			obj.conversion_factor
		)
		target.amount = (flt(obj.qty) - flt(obj.received_qty)) * flt(obj.rate)
		target.base_amount = (
			(flt(obj.qty) - flt(obj.received_qty)) * flt(obj.rate) * flt(source_parent.conversion_rate)
		)

	def select_item(d):
		filtered_items = args.get("filtered_children", [])
		child_filter = d.name in filtered_items if filtered_items else True
		return child_filter

	doc = get_mapped_doc(
		"Purchase Invoice",
		source_name,
		{
			"Purchase Invoice": {
				"doctype": "Purchase Receipt",
				"validation": {
					"docstatus": ["=", 1],
				},
			},
			"Purchase Invoice Item": {
				"doctype": "Purchase Receipt Item",
				"field_map": {
					"name": "purchase_invoice_item",
					"parent": "purchase_invoice",
					"bom": "bom",
					"purchase_order": "purchase_order",
					"po_detail": "purchase_order_item",
					"material_request": "material_request",
					"material_request_item": "material_request_item",
					"wip_composite_asset": "wip_composite_asset",
				},
				"postprocess": update_item,
				"condition": lambda doc: abs(doc.received_qty) < abs(doc.qty) and select_item(doc),
			},
			"Purchase Taxes and Charges": {
				"doctype": "Purchase Taxes and Charges",
				"reset_value": not (args and args.get("merge_taxes")),
				"ignore": args.get("merge_taxes") if args else 0,
			},
		},
		target_doc,
		post_parent_process,
	)

	return doc
