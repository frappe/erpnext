# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

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
def make_subcontract_return(source_name: str, target_doc: Document | str | None = None):
	from erpnext.controllers.sales_and_purchase_return import make_return_doc

	return make_return_doc("Subcontracting Receipt", source_name, target_doc)


@frappe.whitelist()
def make_purchase_receipt(
	source_name: Document | str,
	target_doc: Document | str | None = None,
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

	po_sr_item_dict = {}
	po_name = None
	for item in source_doc.items:
		if not item.purchase_order:
			continue

		if not po_name:
			po_name = item.purchase_order

		po_sr_item_dict[item.purchase_order_item] = {
			"qty": flt(item.qty),
			"rejected_qty": flt(item.rejected_qty),
			"warehouse": item.warehouse,
			"rejected_warehouse": item.rejected_warehouse,
			"subcontracting_receipt_item": item.name,
		}

	if not po_name:
		frappe.throw(
			_("Purchase Order Item reference is missing in Subcontracting Receipt {0}").format(
				source_doc.name
			)
		)

	def update_item(obj, target, source_parent):
		sr_item_details = po_sr_item_dict.get(obj.name)
		ratio = flt(obj.qty) / flt(obj.fg_item_qty)

		target.update(
			{
				"qty": ratio * sr_item_details["qty"],
				"rejected_qty": ratio * sr_item_details["rejected_qty"],
				"warehouse": sr_item_details["warehouse"],
				"rejected_warehouse": sr_item_details["rejected_warehouse"],
				"subcontracting_receipt_item": sr_item_details["subcontracting_receipt_item"],
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
				"condition": lambda doc: doc.name in po_sr_item_dict,
			},
			"Purchase Taxes and Charges": {
				"doctype": "Purchase Taxes and Charges",
				"reset_value": True,
			},
		},
		postprocess=post_process,
	)

	if not target_doc.get("items"):
		add_po_items_to_pr(source_doc, target_doc)

	if (save or submit) and frappe.has_permission(target_doc.doctype, "create"):
		target_doc.save()

		if submit and frappe.has_permission(target_doc.doctype, "submit", target_doc):
			try:
				target_doc.submit()
			except Exception as e:
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
					},
				)
