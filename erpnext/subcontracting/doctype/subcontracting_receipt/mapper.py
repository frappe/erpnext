# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt, get_link_to_form


@frappe.whitelist()
def make_subcontract_return_against_rejected_warehouse(source_name: str):
	from erpnext.controllers.sales_and_purchase_return import make_return_doc

	return make_return_doc("Subcontracting Receipt", source_name, return_against_rejected_qty=True)


@frappe.whitelist()
def make_subcontract_return(source_name: str, target_doc: str | dict | Document | None = None):
	from erpnext.controllers.sales_and_purchase_return import make_return_doc

	return make_return_doc("Subcontracting Receipt", source_name, target_doc)


@frappe.whitelist(methods=["POST"])
def make_purchase_receipt(
	source_name: Document | str,
	target_doc: str | dict | Document | None = None,
	save: bool = False,
	submit: bool = False,
	notify: bool = False,
):
	if isinstance(source_name, str):
		source_doc = frappe.get_doc("Subcontracting Receipt", source_name)
	else:
		source_doc = source_name

	if source_doc.is_return:
		return

	validate_no_purchase_receipt_made(source_doc)

	po_sr_items = defaultdict(list)
	for item in source_doc.items:
		if item.purchase_order:
			po_sr_items[item.purchase_order_item].append(item)

	purchase_orders = list(
		dict.fromkeys(item.purchase_order for item in source_doc.items if item.purchase_order)
	)
	if not purchase_orders:
		frappe.throw(
			_("Purchase Order Item reference is missing in Subcontracting Receipt {0}").format(
				source_doc.name
			)
		)

	def update_item(obj, target, source_parent):
		sr_items = po_sr_items[obj.name]
		ratio = flt(obj.qty) / flt(obj.fg_item_qty)

		target.update(
			{
				"qty": ratio * sum(flt(item.qty) for item in sr_items),
				"rejected_qty": ratio * sum(flt(item.rejected_qty) for item in sr_items),
				"warehouse": sr_items[0].warehouse,
				"rejected_warehouse": next(
					(item.rejected_warehouse for item in sr_items if item.rejected_warehouse), None
				),
				"subcontracting_receipt_item": sr_items[0].name,
			}
		)

	def post_process(source, target):
		target.set_missing_values()
		target.update(
			{
				"posting_date": source_doc.posting_date,
				"posting_time": source_doc.posting_time,
				"subcontracting_receipt": source_doc.name,
				"supplier_warehouse": source_doc.supplier_warehouse,
				"is_subcontracted": 1,
				"currency": frappe.get_cached_value("Company", target.company, "default_currency"),
			}
		)

	target_doc = None
	for po_name in purchase_orders:
		target_doc = get_mapped_doc(
			"Purchase Order",
			po_name,
			{
				"Purchase Order": {
					"doctype": "Purchase Receipt",
					"field_map": {"supplier_warehouse": "supplier_warehouse"},
					"validation": {
						"docstatus": ["=", 1],
					},
				},
				"Purchase Order Item": {
					"doctype": "Purchase Receipt Item",
					"field_map": {
						"name": "purchase_order_item",
						"parent": "purchase_order",
						"bom": "bom",
					},
					"postprocess": update_item,
					"condition": lambda doc: doc.name in po_sr_items,
				},
				"Purchase Taxes and Charges": {
					"doctype": "Purchase Taxes and Charges",
					"reset_value": True,
					# for POs created in earlier version with tax_withholding_row
					"condition": lambda doc: not doc.is_tax_withholding_account,
				},
			},
			target_doc,
			postprocess=post_process,
		)

	if not target_doc.get("items"):
		add_po_items_to_pr(source_doc, target_doc)

	if (save or submit) and frappe.has_permission(target_doc.doctype, "create"):
		target_doc.save()

		if submit and frappe.has_permission(target_doc.doctype, "submit", target_doc):
			frappe.db.savepoint("submit_subcontracting_receipt")
			try:
				target_doc.submit()
			except Exception as e:
				frappe.db.rollback(save_point="submit_subcontracting_receipt")
				target_doc.add_comment("Comment", _("Submit Action Failed") + "<br><br>" + str(e))

		if notify:
			frappe.msgprint(
				_("Purchase Receipt {0} created.").format(
					get_link_to_form(target_doc.doctype, target_doc.name)
				),
				indicator="green",
				alert=True,
			)

	return target_doc


def validate_no_purchase_receipt_made(scr_doc):
	if scr_doc.docstatus != 1:
		frappe.throw(
			_("Submit Subcontracting Receipt {0} before making a Purchase Receipt").format(scr_doc.name)
		)

	validate_single_purchase_receipt(scr_doc.name)


def validate_single_purchase_receipt(subcontracting_receipt, purchase_receipt=None):
	if existing := frappe.db.get_value(
		"Purchase Receipt",
		{
			"subcontracting_receipt": subcontracting_receipt,
			"is_return": 0,
			"docstatus": ("<", 2),
			"name": ("!=", purchase_receipt or ""),
		},
	):
		frappe.throw(
			_("Purchase Receipt {0} is already made against Subcontracting Receipt {1}").format(
				get_link_to_form("Purchase Receipt", existing), subcontracting_receipt
			)
		)


def add_po_items_to_pr(scr_doc, target_doc):
	fg_items = {(item.item_code, item.purchase_order): item.qty for item in scr_doc.items}

	for (item_code, po_name), fg_qty in fg_items.items():
		po_doc = frappe.get_doc("Purchase Order", po_name)
		for item in po_doc.items:
			if item.fg_item != item_code:
				continue

			qty = (item.stock_qty - item.received_qty) * fg_qty / item.fg_item_qty
			if qty:
				target_doc.append(
					"items",
					{
						"item_code": item.item_code,
						"item_name": item.item_name,
						"description": item.description,
						"qty": qty,
						"rate": item.rate,
						"warehouse": item.warehouse,
						"purchase_order": item.parent,
						"purchase_order_item": item.name,
						"project": item.project,
						"cost_center": item.cost_center,
					},
				)
