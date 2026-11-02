from collections import defaultdict

import frappe
from frappe.query_builder.functions import Count
from frappe.utils import flt

from erpnext.stock.doctype.purchase_receipt.services.billing_status import (
	get_billed_amount_against_po,
	get_billed_amount_against_pr,
	get_purchase_receipts_against_po_details,
	update_billed_amount_based_on_po,
	update_billing_percentage,
)


def execute():
	purchase_order_items = get_affected_purchase_order_items()
	if not purchase_order_items:
		return

	updated_purchase_receipts = update_billed_amount_based_on_po(purchase_order_items)
	for purchase_receipt in set(updated_purchase_receipts):
		update_billing_percentage(frappe.get_doc("Purchase Receipt", purchase_receipt))


def get_affected_purchase_order_items() -> list[str]:
	purchase_order_items = get_candidate_purchase_order_items()
	if purchase_order_items:
		purchase_order_items = exclude_purchase_order_items_with_invoice_created_receipts(
			purchase_order_items
		)

	if not purchase_order_items:
		return []

	purchase_receipt_items = get_purchase_receipts_against_po_details(purchase_order_items)
	direct_billed_amounts = get_billed_amount_against_pr([item.name for item in purchase_receipt_items])
	po_billed_amounts = get_billed_amount_against_po(purchase_order_items)

	current_billed_amounts = defaultdict(float)
	available_billed_amounts = defaultdict(float)
	for purchase_order_item, billed_details in po_billed_amounts.items():
		available_billed_amounts[purchase_order_item] = flt(billed_details["billed_amt"])

	for item in purchase_receipt_items:
		current_billed_amounts[item.purchase_order_item] += flt(item.billed_amt)
		available_billed_amounts[item.purchase_order_item] += flt(direct_billed_amounts.get(item.name))

	precision = frappe.get_precision("Purchase Receipt Item", "billed_amt") or 2
	return [
		purchase_order_item
		for purchase_order_item in purchase_order_items
		if flt(po_billed_amounts.get(purchase_order_item, {}).get("billed_amt")) > 0
		and flt(po_billed_amounts.get(purchase_order_item, {}).get("billed_qty")) > 0
		and flt(
			current_billed_amounts[purchase_order_item] - available_billed_amounts[purchase_order_item],
			precision,
		)
		> 0
	]


def exclude_purchase_order_items_with_invoice_created_receipts(purchase_order_items: list[str]) -> list[str]:
	invoice_created_receipt_items = set(
		frappe.get_all(
			"Purchase Receipt Item",
			filters={
				"purchase_order_item": ("in", purchase_order_items),
				"purchase_invoice_item": ("is", "set"),
				"docstatus": 1,
			},
			pluck="purchase_order_item",
		)
	)
	return [item for item in purchase_order_items if item not in invoice_created_receipt_items]


def get_candidate_purchase_order_items() -> list[str]:
	purchase_receipt = frappe.qb.DocType("Purchase Receipt")
	purchase_receipt_item = frappe.qb.DocType("Purchase Receipt Item")
	purchase_invoice = frappe.qb.DocType("Purchase Invoice")
	purchase_invoice_item = frappe.qb.DocType("Purchase Invoice Item")

	purchase_order_items_with_multiple_receipts = (
		frappe.qb.from_(purchase_receipt_item)
		.inner_join(purchase_receipt)
		.on(purchase_receipt_item.parent == purchase_receipt.name)
		.select(purchase_receipt_item.purchase_order_item)
		.where(
			(purchase_receipt.docstatus == 1)
			& (purchase_receipt.is_return == 0)
			& purchase_receipt_item.purchase_order_item.isnotnull()
		)
		.groupby(purchase_receipt_item.purchase_order_item)
		.having(Count(purchase_receipt_item.name) > 1)
	)

	return (
		frappe.qb.from_(purchase_invoice_item)
		.inner_join(purchase_invoice)
		.on(purchase_invoice_item.parent == purchase_invoice.name)
		.select(purchase_invoice_item.po_detail)
		.distinct()
		.where(
			(purchase_invoice.docstatus == 1)
			& (purchase_invoice.update_stock == 0)
			& purchase_invoice_item.pr_detail.isnull()
			& purchase_invoice_item.po_detail.isin(purchase_order_items_with_multiple_receipts)
		)
	).run(pluck=True)
