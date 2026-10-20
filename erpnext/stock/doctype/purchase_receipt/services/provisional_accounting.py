# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Provisional accounting for non-stock items received via Purchase Receipt."""

import frappe
from frappe import _
from frappe.query_builder.functions import IfNull, Sum
from frappe.utils import cint, flt

from erpnext.accounts.utils import get_account_currency


class ProvisionalAccountingService:
	def __init__(self, doc):
		self.doc = doc

	def validate_provisional_expense_account(self) -> None:
		doc = self.doc
		provisional_accounting_for_non_stock_items = cint(
			frappe.db.get_value("Company", doc.company, "enable_provisional_accounting_for_non_stock_items")
		)

		if not provisional_accounting_for_non_stock_items:
			return

		default_provisional_account = doc.get_company_default("default_provisional_account")
		for item in doc.get("items"):
			if not item.get("provisional_expense_account"):
				item.provisional_expense_account = default_provisional_account

	def add_provisional_gl_entry(
		self, item, gl_entries, posting_date, provisional_account, reverse=0, item_amount=None, pr_detail=None
	) -> None:
		doc = self.doc
		credit_currency = get_account_currency(provisional_account)
		expense_account = item.expense_account
		debit_currency = get_account_currency(item.expense_account)
		remarks = doc.get("remarks") or _("Accounting Entry for Service")
		multiplication_factor = 1
		amount = item.base_amount

		if reverse:
			multiplication_factor = -1
			# Post reverse entry for previously posted amount
			amount = item_amount
			expense_account = frappe.db.get_value(
				"Purchase Receipt Item", {"name": pr_detail or item.get("pr_detail")}, ["expense_account"]
			)

		doc.add_gl_entry(
			gl_entries=gl_entries,
			account=provisional_account,
			cost_center=item.cost_center,
			debit=0.0,
			credit=multiplication_factor * amount,
			remarks=remarks,
			against_account=expense_account,
			account_currency=credit_currency,
			project=item.project,
			voucher_detail_no=item.name,
			item=item,
			posting_date=posting_date,
		)

		doc.add_gl_entry(
			gl_entries=gl_entries,
			account=expense_account,
			cost_center=item.cost_center,
			debit=multiplication_factor * amount,
			credit=0.0,
			remarks=remarks,
			against_account=provisional_account,
			account_currency=debit_currency,
			project=item.project,
			voucher_detail_no=item.name,
			item=item,
			posting_date=posting_date,
		)


def get_order_billing_provisional_reversals(invoice) -> dict:
	items = [d for d in invoice.items if d.po_detail and not d.pr_detail]
	if not items:
		return {}

	receipt_rows = get_provisional_receipt_rows(invoice.company, {d.po_detail for d in items})
	if not receipt_rows:
		return {}

	unreversed_qty = get_unreversed_receipt_qty(receipt_rows, invoice)
	posted = get_posted_provision(receipt_rows, invoice)
	factors = get_posted_to_replayed_factors(receipt_rows, unreversed_qty, posted)
	reversals = {}
	for item in items:
		rows = receipt_rows.get(item.po_detail)
		if not rows:
			continue

		if flt(item.qty) < 0:
			allocations = release_receipt_rows(rows, unreversed_qty, -flt(item.qty))
			factor = get_restore_factor(item, allocations, posted, factors[item.po_detail])
		else:
			allocations = allocate_receipt_rows(rows, unreversed_qty, flt(item.qty))
			factor = factors[item.po_detail].open

		reversals[item.name] = [(row, qty * factor) for row, qty in allocations if flt(qty * factor, 9)]

	return reversals


def get_posted_to_replayed_factors(receipt_rows, unreversed_qty, posted) -> dict:
	factors = {}
	for po_detail, rows in receipt_rows.items():
		replayed_open = sum(max(unreversed_qty[row.name], 0) * get_unit_amount(row) for row in rows)
		replayed_reversal = sum(
			(flt(row.kept_qty) - unreversed_qty[row.name]) * get_unit_amount(row) for row in rows
		)
		reversed_amount = flt(posted.reversed.get(po_detail))
		factors[po_detail] = frappe._dict(
			open=get_ratio(flt(posted.booked.get(po_detail)) - reversed_amount, replayed_open),
			reversed=get_ratio(reversed_amount, replayed_reversal),
		)

	return factors


def get_restore_factor(item, allocations, posted, factors) -> float:
	original = posted.invoice_rows.get(item.purchase_invoice_item)
	if not original or not flt(original.qty):
		return factors.reversed

	returned_share = min(1, -flt(item.qty) / flt(original.qty))
	return get_ratio(original.reversed * returned_share, -get_reversal_amount(allocations))


def get_ratio(posted_amount, replayed_amount) -> float:
	if flt(posted_amount, 9) <= 0 or flt(replayed_amount, 9) <= 0:
		return 0.0

	return flt(posted_amount / replayed_amount, 9)


def get_unit_amount(row) -> float:
	return flt(row.rate) * flt(row.conversion_rate)


def get_reversal_amount(allocations) -> float:
	return sum(flt(qty) * get_unit_amount(row) for row, qty in allocations)


def get_posted_provision(receipt_rows, invoice) -> frappe._dict:
	booking_rows = {row.name: po_detail for po_detail, rows in receipt_rows.items() for row in rows}
	booking_rows.update(get_receipt_return_rows(booking_rows))
	other_rows = get_other_invoice_rows(booking_rows, invoice)
	booking_rows.update({name: row.po_detail for name, row in other_rows.items() if row.pr_detail})
	invoice_rows = {name: row for name, row in other_rows.items() if not row.pr_detail}

	accounts = {row.provisional_expense_account for rows in receipt_rows.values() for row in rows}
	balances = get_provisional_balances([*booking_rows, *invoice_rows], accounts, invoice)
	posted = frappe._dict(booked={}, reversed={}, invoice_rows=invoice_rows)
	for name, po_detail in booking_rows.items():
		posted.booked[po_detail] = flt(posted.booked.get(po_detail)) + flt(balances.get(name))

	for po_detail, amount in get_own_receipt_row_reversals(invoice, receipt_rows).items():
		posted.booked[po_detail] = flt(posted.booked.get(po_detail)) - amount

	for name, row in invoice_rows.items():
		row.reversed = -flt(balances.get(name))
		posted.reversed[row.po_detail] = flt(posted.reversed.get(row.po_detail)) + row.reversed

	return posted


def get_own_receipt_row_reversals(invoice, receipt_rows) -> dict:
	if cint(invoice.docstatus) != 1:
		return {}

	rows = {row.name: (po_detail, row) for po_detail, po_rows in receipt_rows.items() for row in po_rows}
	reversals = {}
	for item in invoice.items:
		if item.pr_detail not in rows:
			continue

		po_detail, row = rows[item.pr_detail]
		amount = min(flt(item.qty), flt(row.qty)) * get_unit_amount(row)
		reversals[po_detail] = flt(reversals.get(po_detail)) + amount

	return reversals


def get_receipt_return_rows(booking_rows) -> dict:
	return_rows = frappe.get_all(
		"Purchase Receipt Item",
		filters={"purchase_receipt_item": ("in", list(booking_rows)), "docstatus": 1},
		fields=["name", "purchase_receipt_item"],
	)
	return {row.name: booking_rows[row.purchase_receipt_item] for row in return_rows}


def get_other_invoice_rows(booking_rows, invoice) -> dict:
	pi = frappe.qb.DocType("Purchase Invoice")
	pi_item = frappe.qb.DocType("Purchase Invoice Item")
	rows = (
		frappe.qb.from_(pi_item)
		.join(pi)
		.on(pi.name == pi_item.parent)
		.select(pi_item.name, pi_item.qty, pi_item.pr_detail, pi_item.po_detail)
		.where(
			(pi.docstatus == 1)
			& (pi.name != invoice.name)
			& (
				(pi_item.pr_detail.isin(list(booking_rows)))
				| (pi_item.po_detail.isin(set(booking_rows.values())))
			)
		)
	).run(as_dict=True)

	for row in rows:
		row.po_detail = booking_rows.get(row.pr_detail) or row.po_detail

	return {row.name: row for row in rows}


def get_provisional_balances(names, accounts, invoice) -> dict:
	gle = frappe.qb.DocType("GL Entry")
	return frappe._dict(
		frappe.qb.from_(gle)
		.select(gle.voucher_detail_no, Sum(gle.credit - gle.debit))
		.where(
			(gle.voucher_detail_no.isin(names))
			& (gle.account.isin(accounts))
			& (gle.is_cancelled == 0)
			& (gle.voucher_no != invoice.name)
		)
		.groupby(gle.voucher_detail_no)
		.run()
	)


def get_provisional_receipt_rows(company, po_details) -> dict:
	pr = frappe.qb.DocType("Purchase Receipt")
	pr_item = frappe.qb.DocType("Purchase Receipt Item")
	rows = (
		frappe.qb.from_(pr_item)
		.join(pr)
		.on(pr.name == pr_item.parent)
		.select(
			pr_item.name,
			pr_item.purchase_order_item,
			pr_item.qty,
			pr_item.rate,
			pr_item.provisional_expense_account,
			pr.conversion_rate,
		)
		.where((pr_item.purchase_order_item.isin(po_details)) & (pr.docstatus == 1) & (pr.is_return == 0))
		.orderby(pr.posting_date)
		.orderby(pr.posting_time)
		.orderby(pr.creation)
	).run(as_dict=True)

	default_account = frappe.get_cached_value("Company", company, "default_provisional_account")
	for row in rows:
		row.provisional_expense_account = row.provisional_expense_account or default_account

	return group_rows_with_provisional_entries(rows)


def group_rows_with_provisional_entries(rows) -> dict:
	if not rows:
		return {}

	gle = frappe.qb.DocType("GL Entry")
	rows_with_entries = set(
		(
			frappe.qb.from_(gle)
			.select(gle.voucher_detail_no)
			.distinct()
			.where(
				(gle.voucher_type == "Purchase Receipt")
				& (gle.voucher_detail_no.isin([d.name for d in rows]))
				& (gle.account.isin({d.provisional_expense_account for d in rows}))
				& (gle.is_cancelled == 0)
			)
		).run(pluck=True)
	)

	grouped = {}
	for row in rows:
		if row.name in rows_with_entries:
			grouped.setdefault(row.purchase_order_item, []).append(row)

	return grouped


def get_unreversed_receipt_qty(receipt_rows, invoice) -> dict:
	rows = [row for po_rows in receipt_rows.values() for row in po_rows]
	names = [d.name for d in rows]
	billed_qty = get_invoiced_qty("pr_detail", names)
	returned_qty = get_returned_receipt_qty(names)
	for d in rows:
		d.kept_qty = flt(d.qty) + flt(returned_qty.get(d.name)) - flt(billed_qty.get(d.name))

	unreversed_qty = {d.name: d.kept_qty for d in rows}
	order_billed_qty = get_invoiced_qty("po_detail", list(receipt_rows), invoice)
	for po_detail, po_rows in receipt_rows.items():
		allocate_receipt_rows(po_rows, unreversed_qty, flt(order_billed_qty.get(po_detail)))

	return unreversed_qty


def get_returned_receipt_qty(names) -> dict:
	pr = frappe.qb.DocType("Purchase Receipt")
	pr_item = frappe.qb.DocType("Purchase Receipt Item")
	return frappe._dict(
		frappe.qb.from_(pr_item)
		.join(pr)
		.on(pr.name == pr_item.parent)
		.select(pr_item.purchase_receipt_item, Sum(pr_item.qty))
		.where((pr_item.purchase_receipt_item.isin(names)) & (pr.docstatus == 1) & (pr.is_return == 1))
		.groupby(pr_item.purchase_receipt_item)
		.run()
	)


def get_invoiced_qty(fieldname, names, invoice=None) -> dict:
	pi = frappe.qb.DocType("Purchase Invoice")
	pi_item = frappe.qb.DocType("Purchase Invoice Item")
	query = (
		frappe.qb.from_(pi_item)
		.join(pi)
		.on(pi.name == pi_item.parent)
		.select(pi_item[fieldname], Sum(pi_item.qty))
		.where((pi_item[fieldname].isin(names)) & (pi.docstatus == 1))
		.groupby(pi_item[fieldname])
	)

	if invoice:
		query = query.where((IfNull(pi_item.pr_detail, "") == "") & (pi.name != invoice.name))

	return frappe._dict(query.run())


def allocate_receipt_rows(rows, unreversed_qty, qty) -> list:
	allocations = []
	for row in rows:
		if qty <= 0:
			break

		allocated_qty = min(qty, unreversed_qty[row.name])
		if allocated_qty > 0:
			allocations.append((row, allocated_qty))
			unreversed_qty[row.name] -= allocated_qty
			qty -= allocated_qty

	return allocations


def release_receipt_rows(rows, unreversed_qty, qty) -> list:
	allocations = []
	for row in reversed(rows):
		if qty <= 0:
			break

		released_qty = min(qty, flt(row.kept_qty) - unreversed_qty[row.name])
		if released_qty > 0:
			allocations.append((row, -released_qty))
			unreversed_qty[row.name] += released_qty
			qty -= released_qty

	return allocations
