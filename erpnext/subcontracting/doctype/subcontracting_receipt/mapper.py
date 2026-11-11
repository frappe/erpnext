# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import comma_and, flt, get_link_to_form

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_accounting_dimensions

ROW_BASED_CHARGE_TYPES = ("On Previous Row Amount", "On Previous Row Total")


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

	purchase_orders = get_purchase_orders(source_doc)
	if not purchase_orders:
		frappe.throw(
			_("Purchase Order Item reference is missing in Subcontracting Receipt {0}").format(
				source_doc.name
			)
		)

	if not can_combine_purchase_orders(purchase_orders):
		frappe.throw(get_uncombinable_orders_message(purchase_orders), title=_("Cannot Combine Orders"))

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
			}
		)

	target_doc = None
	first_order_charges = 0
	for po_name in purchase_orders:
		is_first_order = target_doc is None
		charges_before = len(target_doc.taxes) if target_doc else 0
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
					"reset_value": is_first_order,
					# for POs created in earlier version with tax_withholding_row
					"condition": lambda doc: (
						not doc.is_tax_withholding_account and (is_first_order or doc.charge_type == "Actual")
					),
				},
			},
			target_doc,
			postprocess=post_process,
		)
		if is_first_order:
			first_order_charges = len(target_doc.taxes)
		else:
			merge_order_charges(target_doc, first_order_charges, charges_before)

	target_doc.calculate_taxes_and_totals()

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


def get_purchase_orders(scr_doc) -> list[str]:
	return list(dict.fromkeys(item.purchase_order for item in scr_doc.items if item.purchase_order))


def can_combine_purchase_orders(purchase_orders: list[str]) -> bool:
	"""One Purchase Receipt carries one currency, one set of rate-based taxes and one header discount."""
	return len(purchase_orders) < 2 or len(get_purchase_order_terms(purchase_orders)) == 1


def get_purchase_order_terms(purchase_orders: list[str]) -> set[tuple]:
	key_fields = get_charge_key_fields()
	taxes = get_purchase_order_taxes(purchase_orders, key_fields)
	return {
		(order.currency, get_tax_terms(taxes[order.name], key_fields), get_discount_terms(order))
		for order in frappe.get_all(
			"Purchase Order",
			filters={"name": ["in", purchase_orders]},
			fields=[
				"name",
				"currency",
				"apply_discount_on",
				"additional_discount_percentage",
				"discount_amount",
			],
		)
	}


def get_purchase_order_taxes(purchase_orders: list[str], key_fields: list[str]) -> dict[str, list]:
	taxes = defaultdict(list)
	for row in frappe.get_all(
		"Purchase Taxes and Charges",
		filters={
			"parenttype": "Purchase Order",
			"parent": ["in", purchase_orders],
			"is_tax_withholding_account": 0,
		},
		fields=["parent", "charge_type", "row_id", "rate", "included_in_print_rate", *key_fields],
		order_by="idx",
	):
		taxes[row.parent].append(row)

	return taxes


def get_discount_terms(order) -> tuple:
	"""A percentage discount can be shared by orders; an amount discount belongs to its order alone."""
	if flt(order.additional_discount_percentage):
		return (order.apply_discount_on, flt(order.additional_discount_percentage))
	if flt(order.discount_amount):
		return (order.name,)
	return ()


def get_tax_terms(taxes: list, key_fields: list[str]) -> tuple:
	"""Rate-based taxes, plus the Actual charges when a tax is calculated on a previous row."""
	has_row_based_tax = any(row.charge_type in ROW_BASED_CHARGE_TYPES for row in taxes)

	return tuple(
		(
			row.charge_type,
			row.row_id,
			flt(row.rate),
			row.included_in_print_rate,
			*(row.get(field) for field in key_fields),
		)
		for row in taxes
		if has_row_based_tax or row.charge_type != "Actual"
	)


def get_charge_key_fields() -> list[str]:
	return [
		"account_head",
		"category",
		"add_deduct_tax",
		"cost_center",
		"project",
		*get_accounting_dimensions(),
	]


def get_uncombinable_orders_message(purchase_orders: list[str]) -> str:
	return _(
		"Purchase Orders {0} have different currencies, taxes or discounts, so they cannot share one Purchase Receipt. Make one Subcontracting Receipt for each Purchase Order."
	).format(comma_and([get_link_to_form("Purchase Order", name) for name in purchase_orders]))


def merge_order_charges(target_doc, first_order_charges: int, order_charges_start: int):
	"""Fold an order's Actual charges into the first order's rows, matching repeated charges by position."""
	key_fields = get_charge_key_fields()

	def get_charge_key(row) -> tuple:
		return tuple(row.get(field) for field in key_fields)

	first_order_rows = defaultdict(list)
	for row in target_doc.taxes[:first_order_charges]:
		if row.charge_type == "Actual":
			first_order_rows[get_charge_key(row)].append(row)

	for row in target_doc.taxes[order_charges_start:]:
		if matching_rows := first_order_rows.get(get_charge_key(row)):
			first_row = matching_rows.pop(0)
			first_row.tax_amount = flt(first_row.tax_amount) + flt(row.tax_amount)
			target_doc.remove(row)

	for idx, row in enumerate(target_doc.taxes, 1):
		row.idx = idx


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
