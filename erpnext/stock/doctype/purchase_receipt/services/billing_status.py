# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Billing status tracking and PR↔PI billed-amount allocation for Purchase Receipt.

Purchase Invoice imports the module-level allocation helpers from here —
Purchase Receipt owns the shared buying billing logic.
"""

import frappe
from frappe import _
from frappe.query_builder.functions import CombineDatetime
from frappe.utils import flt
from pypika import functions as fn


class BillingStatusService:
	def __init__(self, doc):
		self.doc = doc

	def update_billing_status(self, update_modified: bool = True) -> None:
		doc = self.doc
		updated_pr = [doc.name]
		po_details = []
		for d in doc.get("items"):
			if d.get("purchase_invoice") and d.get("purchase_invoice_item"):
				d.db_set("billed_amt", d.amount, update_modified=update_modified)
			elif d.purchase_order_item:
				po_details.append(d.purchase_order_item)

		if po_details:
			updated_pr += update_billed_amount_based_on_po(po_details, update_modified, doc)

		for pr in set(updated_pr):
			pr_doc = doc if (pr == doc.name) else frappe.get_lazy_doc("Purchase Receipt", pr)
			update_billing_percentage(pr_doc, update_modified=update_modified)


def update_billed_amount_based_on_po(po_details: list, update_modified: bool = True, pr_doc=None) -> list:
	po_billed_amt_details = get_billed_amount_against_po(po_details)

	# Get all Purchase Receipt Item rows against the Purchase Order Items
	pr_details = get_purchase_receipts_against_po_details(po_details)

	pr_items = [pr_detail.name for pr_detail in pr_details]
	pr_items_billed_amount = get_billed_amount_against_pr(pr_items)

	updated_pr = []
	for pr_item in pr_details:
		billed_amt_against_po, billed_qty_against_po = 0, 0
		if billed_details := po_billed_amt_details.get(pr_item.purchase_order_item):
			billed_amt_against_po = flt(billed_details["billed_amt"])
			billed_qty_against_po = flt(billed_details["billed_qty"])

		# Get billed amount directly against Purchase Receipt
		billed_amt_against_pr = flt(pr_items_billed_amount.get(pr_item.name, 0))

		# Distribute billed amount directly against PO between PRs based on FIFO
		if billed_amt_against_po and billed_amt_against_pr < pr_item.amount:
			if not billed_amt_against_pr and billed_qty_against_po and billed_qty_against_po > pr_item.qty:
				billed_amt_against_pr = flt(flt(billed_amt_against_po) * flt(pr_item.qty)) / flt(
					billed_qty_against_po
				)

				# Deduct the amount and qty consumed by this PR so that the next PR
				# against the same PO Item does not get billed for the same amount again.
				po_billed_amt_details[pr_item.purchase_order_item]["billed_amt"] = (
					billed_amt_against_po - billed_amt_against_pr
				)
				po_billed_amt_details[pr_item.purchase_order_item]["billed_qty"] = (
					billed_qty_against_po - pr_item.qty
				)
			else:
				pending_to_bill = flt(pr_item.amount) - billed_amt_against_pr
				consumed_amt_against_po = min(pending_to_bill, billed_amt_against_po)
				billed_amt_against_pr += consumed_amt_against_po

				po_billed_amt_details[pr_item.purchase_order_item]["billed_amt"] = (
					billed_amt_against_po - consumed_amt_against_po
				)
				po_billed_amt_details[pr_item.purchase_order_item]["billed_qty"] = billed_qty_against_po * (
					1 - consumed_amt_against_po / billed_amt_against_po
				)

		if pr_item.billed_amt != billed_amt_against_pr:
			# update existing doc if possible
			if pr_doc and pr_item.parent == pr_doc.name:
				pr_item = next((item for item in pr_doc.items if item.name == pr_item.name), None)
				pr_item.db_set("billed_amt", billed_amt_against_pr, update_modified=update_modified)

			else:
				frappe.db.set_value(
					"Purchase Receipt Item",
					pr_item.name,
					"billed_amt",
					billed_amt_against_pr,
					update_modified=update_modified,
				)

			updated_pr.append(pr_item.parent)

	return updated_pr


def get_purchase_receipts_against_po_details(po_details: list) -> list[dict]:
	# Get Purchase Receipts against Purchase Order Items

	purchase_receipt = frappe.qb.DocType("Purchase Receipt")
	purchase_receipt_item = frappe.qb.DocType("Purchase Receipt Item")

	query = (
		frappe.qb.from_(purchase_receipt)
		.inner_join(purchase_receipt_item)
		.on(purchase_receipt.name == purchase_receipt_item.parent)
		.select(
			purchase_receipt_item.name,
			purchase_receipt_item.qty,
			purchase_receipt_item.rejected_qty,
			purchase_receipt_item.parent,
			purchase_receipt_item.amount,
			purchase_receipt_item.billed_amt,
			purchase_receipt_item.purchase_order_item,
		)
		.where(
			(purchase_receipt_item.purchase_order_item.isin(po_details))
			& (purchase_receipt.docstatus == 1)
			& (purchase_receipt.is_return == 0)
		)
		.orderby(CombineDatetime(purchase_receipt.posting_date, purchase_receipt.posting_time))
		.orderby(purchase_receipt.name)
	)

	return query.run(as_dict=True)


def get_billed_amount_against_pr(pr_items: list) -> dict:
	# Get billed amount directly against Purchase Receipt

	if not pr_items:
		return {}

	purchase_invoice_item = frappe.qb.DocType("Purchase Invoice Item")

	query = (
		frappe.qb.from_(purchase_invoice_item)
		.select(fn.Sum(purchase_invoice_item.amount).as_("billed_amt"), purchase_invoice_item.pr_detail)
		.where((purchase_invoice_item.pr_detail.isin(pr_items)) & (purchase_invoice_item.docstatus == 1))
		.groupby(purchase_invoice_item.pr_detail)
	).run(as_dict=1)

	return {d.pr_detail: flt(d.billed_amt) for d in query}


def get_billed_amount_against_po(po_items: list) -> dict:
	# Get billed amount directly against Purchase Order
	if not po_items:
		return {}

	purchase_invoice = frappe.qb.DocType("Purchase Invoice")
	purchase_invoice_item = frappe.qb.DocType("Purchase Invoice Item")

	query = (
		frappe.qb.from_(purchase_invoice_item)
		.inner_join(purchase_invoice)
		.on(purchase_invoice_item.parent == purchase_invoice.name)
		.select(
			fn.Sum(purchase_invoice_item.amount).as_("billed_amt"),
			fn.Sum(purchase_invoice_item.qty).as_("qty"),
			purchase_invoice_item.po_detail,
		)
		.where(
			(purchase_invoice_item.po_detail.isin(po_items))
			& (purchase_invoice.docstatus == 1)
			& (purchase_invoice_item.pr_detail.isnull())
			& (purchase_invoice.update_stock == 0)
		)
		.groupby(purchase_invoice_item.po_detail)
	).run(as_dict=1)

	return {d.po_detail: {"billed_amt": flt(d.billed_amt), "billed_qty": flt(d.qty)} for d in query}


def update_billing_percentage(
	pr_doc, update_modified: bool = True, adjust_incoming_rate: bool = False
) -> None:
	buying_settings = frappe.get_single("Buying Settings")
	bill_for_rejected = buying_settings.bill_for_rejected_quantity_in_purchase_invoice
	items = [item for item in pr_doc.items if not item.closed] or pr_doc.items

	if buying_settings.set_landed_cost_based_on_purchase_invoice_rate:
		percent_billed = get_percent_billed_by_qty(pr_doc, items, bill_for_rejected)
	else:
		percent_billed = get_percent_billed_by_amount(pr_doc, items, bill_for_rejected)

	pr_doc.db_set("per_billed", percent_billed)

	if update_modified:
		pr_doc.set_status(update=True)
		pr_doc.notify_update()

	if adjust_incoming_rate:
		set_amount_difference_with_purchase_invoice(pr_doc, items)
		adjust_incoming_rate_for_pr(pr_doc)


def get_percent_billed_by_amount(pr_doc, items: list, bill_for_rejected: bool) -> float:
	over_billing_allowance, role_allowed_to_over_bill = frappe.get_single_value(
		"Accounts Settings", ["over_billing_allowance", "role_allowed_to_over_bill"]
	)

	total_amount, total_billed_amount = 0, 0
	item_wise_returned_qty = get_item_wise_returned_qty([item.name for item in pr_doc.items])

	for item in items:
		returned_qty = flt(item_wise_returned_qty.get(item.name))
		returned_amount = flt(returned_qty) * flt(item.rate)
		pending_amount = flt(item.amount) - returned_amount

		# When rejected qty is billable, its value is part of the billable base too
		rejected_amount = 0.0
		if bill_for_rejected:
			rejected_amount = flt(item.rejected_qty * item.rate, item.precision("amount"))
			pending_amount = flt(item.amount) + rejected_amount

		total_billable_amount = abs(flt(item.amount) + rejected_amount)
		if pending_amount > 0:
			total_billable_amount = pending_amount if item.billed_amt <= pending_amount else item.billed_amt

		total_amount += total_billable_amount
		total_billed_amount += abs(flt(item.billed_amt))

		if pr_doc.get("is_return") and not total_amount and total_billed_amount:
			total_amount = total_billed_amount

		amount = flt(item.amount) + rejected_amount

		if amount and item.billed_amt > amount:
			per_over_billed = (flt(item.billed_amt / amount, 2) * 100) - 100
			if (
				per_over_billed > over_billing_allowance
				and role_allowed_to_over_bill not in frappe.get_roles()
			):
				frappe.throw(
					_("Over Billing Allowance exceeded for Purchase Receipt Item {0} ({1}) by {2}%").format(
						item.name, frappe.bold(item.item_code), per_over_billed - over_billing_allowance
					)
				)

	return round(100 * (total_billed_amount / (total_amount or 1)), 6)


def get_percent_billed_by_qty(pr_doc, items: list, bill_for_rejected: bool) -> float:
	"""Share of each row's qty that is invoiced, weighted by the row's value."""
	returned_qty = get_item_wise_returned_qty([item.name for item in pr_doc.items])
	invoiced_qty = get_invoiced_qty(pr_doc, bill_for_rejected)

	total_value, billed_value = 0.0, 0.0
	for item in items:
		billable_qty = get_billable_qty(item, returned_qty.get(item.name), bill_for_rejected)
		if not billable_qty:
			continue

		value = abs(billable_qty * flt(item.rate))
		total_value += value
		billed_value += value * min(flt(invoiced_qty.get(item.name)) / billable_qty, 1)

	return round(100 * (billed_value / (total_value or 1)), 6)


def get_billable_qty(item, returned_qty: float | None, bill_for_rejected: bool) -> float:
	if bill_for_rejected:
		return flt(item.qty) + flt(item.rejected_qty)

	pending_qty = flt(item.qty) - flt(returned_qty)
	return pending_qty if pending_qty > 0 else flt(item.qty)


def get_invoiced_qty(pr_doc, bill_for_rejected: bool) -> dict:
	"""Invoiced qty per Purchase Receipt Item, with Purchase Order invoices spread across receipts."""
	billed = get_billed_qty_amount_against_purchase_receipt([item.name for item in pr_doc.items])
	invoiced_qty = {pr_detail: row["qty"] for pr_detail, row in billed.items()}

	po_details = [item.purchase_order_item for item in pr_doc.items if item.purchase_order_item]
	if po_details:
		invoiced_qty.update(get_invoiced_qty_based_on_po(po_details, bill_for_rejected))

	for item in pr_doc.items:
		if item.purchase_invoice_item:
			invoiced_qty[item.name] = flt(item.qty)

	return invoiced_qty


def get_invoiced_qty_based_on_po(po_details: list, bill_for_rejected: bool) -> dict:
	"""Fill receipts FIFO with the qty invoiced directly against the Purchase Order."""
	po_billed = get_billed_amount_against_po(po_details)
	pending_po_qty = {po_detail: row["billed_qty"] for po_detail, row in po_billed.items()}

	pr_items = get_purchase_receipts_against_po_details(po_details)
	pr_item_names = [pr_item.name for pr_item in pr_items]
	billed_against_pr = get_billed_qty_amount_against_purchase_receipt(pr_item_names)
	returned_qty = get_item_wise_returned_qty(pr_item_names)

	invoiced_qty = {}
	for pr_item in pr_items:
		direct_qty = flt(billed_against_pr.get(pr_item.name, {}).get("qty"))
		billable_qty = get_billable_qty(pr_item, returned_qty.get(pr_item.name), bill_for_rejected)
		available_qty = flt(pending_po_qty.get(pr_item.purchase_order_item))
		qty_from_po = max(min(billable_qty - direct_qty, available_qty), 0)

		pending_po_qty[pr_item.purchase_order_item] = available_qty - qty_from_po
		invoiced_qty[pr_item.name] = direct_qty + qty_from_po

	return invoiced_qty


def set_amount_difference_with_purchase_invoice(pr_doc, items: list) -> None:
	billed_qty_amt = get_billed_qty_amount_against_purchase_receipt([item.name for item in pr_doc.items])
	billed_qty_amt_based_on_po = get_billed_qty_amount_against_purchase_order(pr_doc)

	for item in items:
		adjusted_amt = 0.0

		if (
			item.billed_amt is not None
			and item.amount is not None
			and (billed_qty_amt.get(item.name) or billed_qty_amt_based_on_po.get(item.purchase_order_item))
		):
			qty = None
			if billed_qty_amt.get(item.name):
				qty = billed_qty_amt.get(item.name).get("qty")

			if not qty and billed_qty_amt_based_on_po.get(item.purchase_order_item):
				if item.qty < billed_qty_amt_based_on_po.get(item.purchase_order_item)["qty"]:
					qty = item.qty
				else:
					qty = billed_qty_amt_based_on_po.get(item.purchase_order_item)["qty"]

				billed_qty_amt_based_on_po[item.purchase_order_item]["qty"] -= qty

			billed_amt = item.billed_amt
			if billed_qty_amt.get(item.name):
				billed_amt = flt(billed_qty_amt.get(item.name).get("amount"))
			elif billed_qty_amt_based_on_po.get(item.purchase_order_item):
				total_billed_qty = billed_qty_amt_based_on_po.get(item.purchase_order_item).get("qty") + qty

				if total_billed_qty:
					billed_amt = flt(
						flt(billed_qty_amt_based_on_po.get(item.purchase_order_item).get("amount"))
						* (qty / total_billed_qty)
					)
				else:
					billed_amt = 0.0

				# Reduce billed amount based on PO for next iterations
				billed_qty_amt_based_on_po[item.purchase_order_item]["amount"] -= billed_amt

			if qty:
				adjusted_amt = (
					flt(billed_amt / qty) - (flt(item.rate) * flt(pr_doc.conversion_rate))
				) * item.qty

		adjusted_amt = flt(adjusted_amt, item.precision("amount"))
		item.db_set("amount_difference_with_purchase_invoice", adjusted_amt, update_modified=False)


def get_billed_qty_amount_against_purchase_receipt(pr_names: list) -> dict:
	if not pr_names:
		return frappe._dict()

	parent_table = frappe.qb.DocType("Purchase Invoice")
	table = frappe.qb.DocType("Purchase Invoice Item")
	query = (
		frappe.qb.from_(parent_table)
		.inner_join(table)
		.on(parent_table.name == table.parent)
		.select(
			table.pr_detail,
			fn.Sum(table.base_net_amount).as_("amount"),
			fn.Sum(table.qty).as_("qty"),
		)
		.where((table.pr_detail.isin(pr_names)) & (table.docstatus == 1))
		.groupby(table.pr_detail)
	)
	invoice_data = query.run(as_dict=1)

	if not invoice_data:
		return frappe._dict()

	billed_qty_amt = frappe._dict()

	for row in invoice_data:
		if row.pr_detail not in billed_qty_amt:
			billed_qty_amt[row.pr_detail] = {"amount": 0, "qty": 0}

		billed_qty_amt[row.pr_detail]["amount"] += flt(row.amount)
		billed_qty_amt[row.pr_detail]["qty"] += flt(row.qty)

	return billed_qty_amt


def get_billed_qty_amount_against_purchase_order(pr_doc) -> dict:
	po_names = list(
		set(
			[
				d.purchase_order_item
				for d in pr_doc.items
				if d.purchase_order_item and not d.purchase_invoice_item
			]
		)
	)

	invoice_data_po_based = frappe._dict()
	if po_names:
		parent_table = frappe.qb.DocType("Purchase Invoice")
		table = frappe.qb.DocType("Purchase Invoice Item")

		query = (
			frappe.qb.from_(parent_table)
			.inner_join(table)
			.on(parent_table.name == table.parent)
			.select(
				table.po_detail,
				fn.Sum(table.qty).as_("qty"),
				fn.Sum(table.base_net_amount).as_("amount"),
			)
			.where((table.po_detail.isin(po_names)) & (table.docstatus == 1) & (table.pr_detail.isnull()))
			.groupby(table.po_detail)
		)

		invoice_data = query.run(as_dict=1)
		if not invoice_data:
			return frappe._dict()

		for row in invoice_data:
			if row.po_detail not in invoice_data_po_based:
				invoice_data_po_based[row.po_detail] = {"amount": 0, "qty": 0}

			invoice_data_po_based[row.po_detail]["amount"] += flt(row.amount)
			invoice_data_po_based[row.po_detail]["qty"] += flt(row.qty)

	return invoice_data_po_based


def adjust_incoming_rate_for_pr(doc) -> None:
	doc.update_valuation_rate(reset_outgoing_rate=False)

	for item in doc.get("items"):
		item.db_update()

	if doc.doctype == "Purchase Receipt":
		doc.enable_recalculate_rate_in_sles()

	doc.repost_future_sle_and_gle(force=True)


def get_item_wise_returned_qty(items: list) -> dict:
	return frappe._dict(
		frappe.get_all(
			"Purchase Receipt",
			fields=[
				"`tabPurchase Receipt Item`.purchase_receipt_item",
				{"SUM": [{"ABS": "`tabPurchase Receipt Item`.qty"}], "as": "qty"},
			],
			filters=[
				["Purchase Receipt", "docstatus", "=", 1],
				["Purchase Receipt", "is_return", "=", 1],
				["Purchase Receipt Item", "purchase_receipt_item", "in", items],
			],
			group_by="`tabPurchase Receipt Item`.purchase_receipt_item",
			as_list=1,
		)
	)
