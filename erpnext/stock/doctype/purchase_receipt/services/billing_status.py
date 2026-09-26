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
	pr_doc, update_modified: bool = True, adjust_incoming_rate: bool = False, invoiced: dict | None = None
) -> None:
	"""`invoiced` from get_invoiced_qty_and_amount lets receipts on one order line share its invoice split."""
	buying_settings = frappe.get_single("Buying Settings")
	bill_for_rejected = buying_settings.bill_for_rejected_quantity_in_purchase_invoice
	items = [item for item in pr_doc.items if not item.closed] or pr_doc.items

	if buying_settings.set_landed_cost_based_on_purchase_invoice_rate:
		if invoiced is None:
			invoiced = get_invoiced_qty_and_amount(pr_doc.items, bill_for_rejected)
		percent_billed = get_percent_billed_by_qty(pr_doc, items, bill_for_rejected, invoiced)
	else:
		percent_billed = get_percent_billed_by_amount(pr_doc, items, bill_for_rejected)

	pr_doc.db_set("per_billed", percent_billed)

	if update_modified:
		pr_doc.set_status(update=True)
		pr_doc.notify_update()

	if adjust_incoming_rate:
		set_amount_difference_with_purchase_invoice(items, invoiced)
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


def is_billed_by_qty() -> bool:
	"""Invoice-rate landed cost leaves qty as the only stable measure of billing."""
	return bool(
		frappe.db.get_single_value("Buying Settings", "set_landed_cost_based_on_purchase_invoice_rate")
	)


def get_percent_billed_by_qty(pr_doc, items: list, bill_for_rejected: bool, invoiced: dict) -> float:
	billable_qty = get_billable_qty_by_row(pr_doc, items, bill_for_rejected)
	return get_qty_based_percent_billed(items, billable_qty, get_invoiced_qty(pr_doc, invoiced))


def get_qty_based_percent_billed(items: list, billable_qty: dict, invoiced_qty: dict) -> float:
	"""Share of each row's billable qty that is invoiced, weighted by the row's value, or by qty when no row has one."""
	weigh_by_value = any(flt(item.rate) for item in items)

	total_weight, billed_weight = 0.0, 0.0
	for item in items:
		qty = flt(billable_qty.get(item.name))
		if not qty:
			continue

		weight = abs(qty * flt(item.rate)) if weigh_by_value else abs(qty)
		total_weight += weight
		billed_weight += weight * min(flt(invoiced_qty.get(item.name)) / qty, 1)

	return round(100 * (billed_weight / (total_weight or 1)), 6)


def get_billable_qty_by_row(pr_doc, items: list, bill_for_rejected: bool) -> dict:
	"""Qty left to bill per row; a receipt returned in full is measured against what it received."""
	returned_qty = get_item_wise_returned_qty([item.name for item in pr_doc.items])
	billable_qty = {
		item.name: get_billable_qty(item, returned_qty.get(item.name), bill_for_rejected) for item in items
	}
	if any(qty > 0 for qty in billable_qty.values()):
		return billable_qty

	return {item.name: flt(item.qty) for item in items}


def get_billable_qty(item, returned_qty: float | None, bill_for_rejected: bool) -> float:
	if bill_for_rejected:
		return flt(item.qty) + flt(item.rejected_qty)

	return flt(item.qty) - flt(returned_qty)


def get_invoiced_qty(pr_doc, invoiced: dict) -> dict:
	invoiced_qty = {name: row.qty for name, row in invoiced.items()}

	for item in pr_doc.items:
		if item.purchase_invoice_item:
			invoiced_qty[item.name] = flt(item.qty)

	return invoiced_qty


def get_invoiced_qty_and_amount(pr_items: list, bill_for_rejected: bool) -> dict:
	"""Invoiced qty and base amount per Purchase Receipt Item, direct and through the Purchase Order."""
	billed = get_billed_qty_amount_against_purchase_receipt([item.name for item in pr_items])
	invoiced = {
		pr_detail: frappe._dict(qty=flt(row["qty"]), amount=flt(row["amount"]))
		for pr_detail, row in billed.items()
	}

	po_details = list({item.purchase_order_item for item in pr_items if item.purchase_order_item})
	po_invoice_share = get_po_invoice_share(po_details, bill_for_rejected) if po_details else {}

	for item in pr_items:
		share = po_invoice_share.get(item.name)
		if not share or item.purchase_invoice_item:
			continue

		row = invoiced.setdefault(item.name, frappe._dict(qty=0.0, amount=0.0))
		row.qty += share.qty
		row.amount += share.amount

	return invoiced


def get_po_invoice_share(po_details: list, bill_for_rejected: bool) -> dict:
	"""Split invoices made against the Purchase Order over its receipts, oldest invoice to oldest receipt."""
	po_invoices = get_po_invoices(po_details)

	pr_items = get_purchase_receipts_against_po_details(po_details)
	pr_item_names = [pr_item.name for pr_item in pr_items]
	billed_against_pr = get_billed_qty_amount_against_purchase_receipt(pr_item_names)
	returned_qty = get_item_wise_returned_qty(pr_item_names)

	share = {}
	for pr_item in pr_items:
		direct_qty = flt(billed_against_pr.get(pr_item.name, {}).get("qty"))
		billable_qty = get_billable_qty(pr_item, returned_qty.get(pr_item.name), bill_for_rejected)
		invoices = po_invoices.get(pr_item.purchase_order_item, [])
		share[pr_item.name] = take_from_invoices(invoices, billable_qty - direct_qty)

	return share


def take_from_invoices(invoices: list, pending_qty: float) -> frappe._dict:
	"""Take qty from the oldest invoices first, each at its own rate."""
	taken = frappe._dict(qty=0.0, amount=0.0)
	for invoice in invoices:
		qty = min(invoice.qty, pending_qty - taken.qty)
		if qty <= 0:
			continue

		amount = invoice.amount * qty / invoice.qty
		invoice.qty -= qty
		invoice.amount -= amount
		taken.qty += qty
		taken.amount += amount

	return taken


def get_po_invoices(po_details: list) -> dict:
	"""Net qty and base amount of each invoice made against the Purchase Order, oldest first."""
	purchase_invoice = frappe.qb.DocType("Purchase Invoice")
	purchase_invoice_item = frappe.qb.DocType("Purchase Invoice Item")

	rows = (
		frappe.qb.from_(purchase_invoice_item)
		.inner_join(purchase_invoice)
		.on(purchase_invoice_item.parent == purchase_invoice.name)
		.select(
			purchase_invoice_item.po_detail,
			purchase_invoice_item.qty,
			purchase_invoice_item.base_net_amount,
			purchase_invoice.name,
			purchase_invoice.is_return,
			purchase_invoice.return_against,
		)
		.where(
			(purchase_invoice_item.po_detail.isin(po_details))
			& ((purchase_invoice_item.pr_detail.isnull()) | (purchase_invoice_item.pr_detail == ""))
			& (purchase_invoice.docstatus == 1)
			& (purchase_invoice.update_stock == 0)
		)
		.orderby(CombineDatetime(purchase_invoice.posting_date, purchase_invoice.posting_time))
		.orderby(purchase_invoice.name)
		.orderby(purchase_invoice_item.idx)
	).run(as_dict=True)

	po_invoices = {}
	for row in rows:
		invoice_name = row.return_against if row.is_return else row.name
		invoices = po_invoices.setdefault(row.po_detail, {})
		invoice = invoices.setdefault(invoice_name, frappe._dict(qty=0.0, amount=0.0))
		invoice.qty += flt(row.qty)
		invoice.amount += flt(row.base_net_amount)

	return {po_detail: list(invoices.values()) for po_detail, invoices in po_invoices.items()}


def get_invoiced_qty_against_po_items(po_items: list) -> dict:
	"""Invoiced qty per Purchase Order Item, leaving out returns that do not touch the order."""
	purchase_invoice = frappe.qb.DocType("Purchase Invoice")
	purchase_invoice_item = frappe.qb.DocType("Purchase Invoice Item")

	query = (
		frappe.qb.from_(purchase_invoice_item)
		.inner_join(purchase_invoice)
		.on(purchase_invoice_item.parent == purchase_invoice.name)
		.select(purchase_invoice_item.po_detail, fn.Sum(purchase_invoice_item.qty))
		.where(
			(purchase_invoice_item.po_detail.isin(po_items))
			& (purchase_invoice.docstatus == 1)
			& (
				(purchase_invoice.is_return == 0)
				| (purchase_invoice.update_billed_amount_in_purchase_order == 1)
			)
		)
		.groupby(purchase_invoice_item.po_detail)
	)

	return frappe._dict(query.run())


def set_amount_difference_with_purchase_invoice(items: list, invoiced: dict) -> None:
	for item in items:
		adjusted_amt = 0.0
		row = invoiced.get(item.name)
		if row and row.qty:
			adjusted_amt = flt(row.amount / row.qty) * flt(item.qty) - flt(item.base_net_amount)

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
		.where(
			(table.pr_detail.isin(pr_names))
			& (table.docstatus == 1)
			& ((parent_table.is_return == 0) | (parent_table.update_billed_amount_in_purchase_receipt == 1))
		)
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
