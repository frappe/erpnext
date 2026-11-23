# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""All database reads of the cash basis calculation.

Each function runs a fixed number of queries for a company, not one for each voucher.
The other modules of the calculation do not query the database.
"""

import frappe
from frappe.query_builder.functions import Sum
from frappe.utils import flt

from erpnext.accounts.cash_basis.deferrals import DEFERRAL_JOURNAL_TYPES, DeferredItem
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_accounting_dimensions

CONVERTIBLE_PARTY_TYPES = ("Customer", "Supplier")
BATCH_SIZE = 5000

INVOICE_FIELDS = {
	"Sales Invoice": (
		"name",
		"posting_date",
		"is_pos",
		"is_return",
		"conversion_rate",
		"base_paid_amount",
		"base_change_amount",
		"base_write_off_amount",
		"write_off_amount",
		"loyalty_amount",
		"write_off_account",
		"loyalty_redemption_account",
	),
	"Purchase Invoice": (
		"name",
		"posting_date",
		"is_paid",
		"is_return",
		"conversion_rate",
		"base_paid_amount",
		"base_write_off_amount",
		"write_off_amount",
		"write_off_account",
	),
}


def get_dimension_fields() -> list[str]:
	return get_accounting_dimensions()


def get_dimension_doctypes() -> dict[str, str]:
	"""Each filter field of a dimension, with its document type."""
	dimensions = {"cost_center": "Cost Center", "project": "Project"}
	dimensions.update({d.fieldname: d.document_type for d in get_accounting_dimensions(as_list=False)})
	return dimensions


def get_period_closing_vouchers(company: str, to_date) -> list[dict]:
	pcv = frappe.qb.DocType("Period Closing Voucher")
	return (
		frappe.qb.from_(pcv)
		.select(pcv.name, pcv.period_start_date, pcv.period_end_date, pcv.closing_account_head)
		.where((pcv.company == company) & (pcv.docstatus == 1) & (pcv.period_end_date <= to_date))
		.where(pcv.gle_processing_status == "Completed")
		.orderby(pcv.period_end_date)
		.run(as_dict=True)
	)


def get_company_defaults(company: str) -> tuple[str, str | None]:
	"""The currency and the default cost center of the company."""
	currency, cost_center = frappe.get_cached_value("Company", company, ["default_currency", "cost_center"])
	return currency, cost_center


def get_payment_ledger_rows(company: str, to_date) -> list[dict]:
	"""Query 1: the PLE rows of the company to the date, for all party types."""
	ple = frappe.qb.DocType("Payment Ledger Entry")
	return (
		frappe.qb.from_(ple)
		.select(
			ple.name,
			ple.posting_date,
			ple.account,
			ple.party_type,
			ple.party,
			ple.voucher_type,
			ple.voucher_no,
			ple.against_voucher_type,
			ple.against_voucher_no,
			ple.amount,
			ple.amount_in_account_currency,
			ple.account_currency,
			ple.cost_center,
			ple.finance_book,
		)
		.where((ple.company == company) & (ple.delinked == 0) & (ple.posting_date <= to_date))
		.orderby(ple.posting_date)
		.orderby(ple.creation)
		.run(as_dict=True)
	)


def get_gl_rows(company: str, voucher_nos, to_date) -> list[dict]:
	"""Query 2: the GL rows of the given vouchers to the date, in batches."""
	gle = frappe.qb.DocType("GL Entry")
	fields = gl_row_fields(gle)
	rows = []
	for batch in batches(sorted(set(voucher_nos))):
		rows.extend(
			frappe.qb.from_(gle)
			.select(*fields)
			.where(
				(gle.company == company)
				& (gle.is_cancelled == 0)
				& (gle.posting_date <= to_date)
				& (gle.voucher_no.isin(batch))
			)
			.orderby(gle.posting_date)
			.orderby(gle.creation)
			.run(as_dict=True)
		)
	return rows


def gl_row_fields(gle) -> list:
	"""The GL Entry fields that the calculation reads."""
	dimension_fields = get_dimension_fields()
	return [
		gle.name,
		gle.voucher_type,
		gle.voucher_no,
		gle.posting_date,
		gle.account,
		gle.party_type,
		gle.party,
		gle.debit,
		gle.credit,
		gle.debit_in_account_currency,
		gle.credit_in_account_currency,
		gle.account_currency,
		gle.against,
		gle.against_voucher_type,
		gle.against_voucher,
		gle.cost_center,
		gle.project,
		gle.finance_book,
		gle.is_opening,
		gle.remarks,
		gle.voucher_detail_no,
		*[gle[fieldname] for fieldname in dimension_fields],
	]


def get_account_details(company: str) -> dict[str, frappe._dict]:
	account = frappe.qb.DocType("Account")
	rows = (
		frappe.qb.from_(account)
		.select(account.name, account.report_type, account.root_type, account.account_type)
		.where(account.company == company)
		.run(as_dict=True)
	)
	return {row.name: row for row in rows}


def get_invoice_headers(doctype: str, names) -> dict[str, frappe._dict]:
	"""Query 3: the header fields of invoices for self-settlement and returns."""
	table = frappe.qb.DocType(doctype)
	headers = {}
	for batch in batches(sorted(set(names))):
		query = frappe.qb.from_(table).select(*[table[f] for f in INVOICE_FIELDS[doctype]])
		for row in query.where(table.name.isin(batch)).run(as_dict=True):
			headers[row.name] = row
	return headers


DEFERRED_ITEM_FIELDS = {
	"Sales Invoice": (
		"Sales Invoice Item",
		"enable_deferred_revenue",
		"deferred_revenue_account",
		"income_account",
	),
	"Purchase Invoice": (
		"Purchase Invoice Item",
		"enable_deferred_expense",
		"deferred_expense_account",
		"expense_account",
	),
}


def get_deferred_items(doctype: str, names) -> dict[str, list]:
	"""The deferred revenue or deferred expense items of the invoices, by invoice.

	The project and the accounting dimensions are those of the GL row of the item: the value of
	the item, else the value of the invoice (get_gl_dict). The amount is that of the GL row too.
	"""
	item_doctype, flag, deferred_field, account_field = DEFERRED_ITEM_FIELDS[doctype]
	item, invoice = frappe.qb.DocType(item_doctype), frappe.qb.DocType(doctype)
	dimension_fields = ["project", *get_dimension_fields()]
	discount_fields = []
	if doctype == "Sales Invoice":
		discount_fields = [
			item.base_amount,
			item.distributed_discount_amount,
			item.discount_amount.as_("item_discount_amount"),
			item.discount_account,
			item.qty,
			invoice.discount_amount,
			invoice.additional_discount_account,
			invoice.conversion_rate,
		]
	items = {}
	for batch in batches(sorted(set(names))):
		rows = (
			frappe.qb.from_(item)
			.join(invoice)
			.on(invoice.name == item.parent)
			.select(
				item.parent,
				item.name,
				item[deferred_field].as_("deferred_account"),
				item[account_field].as_("account"),
				item.cost_center,
				item.base_net_amount,
				*discount_fields,
				*[item[f].as_(f"item_{f}") for f in dimension_fields],
				*[invoice[f].as_(f"invoice_{f}") for f in dimension_fields],
			)
			.where((item.parent.isin(batch)) & (item[flag] == 1))
			.orderby(item.parent)
			.orderby(item.idx)
			.run(as_dict=True)
		)
		before_discount = get_invoices_posted_before_discount(doctype, rows)
		for row in rows:
			dimensions = {f: row[f"item_{f}"] or row[f"invoice_{f}"] for f in dimension_fields}
			items.setdefault(row.parent, []).append(
				DeferredItem(
					row.name,
					row.deferred_account,
					row.account,
					row.cost_center,
					row.gl_amount if row.parent in before_discount else row.base_net_amount,
					dimensions,
				)
			)
	return items


def get_invoices_posted_before_discount(doctype: str, rows) -> set:
	"""The invoices posted with discount accounting, as the GL shows. Sets `gl_amount` on each row.

	With discount accounting at posting, the deferred row of an item is the amount of
	`get_amount_and_base_amount` plus the item discount row (`make_discount_gl_entries`). The
	setting can change after posting, and "Is Cash or Non Trade Discount" posts a discount row
	too. So compare the posted total of the deferred rows of the invoice with both amounts.
	"""
	if doctype != "Sales Invoice" or not rows:
		return set()
	names = {row.parent for row in rows}
	distributed = get_invoices_with_distributed_discount(names)
	net, gross = {}, {}
	for row in rows:
		row.gl_amount = get_item_amount_with_discount_accounting(row, row.parent in distributed)
		net[row.parent] = net.get(row.parent, 0.0) + flt(row.base_net_amount)
		gross[row.parent] = gross.get(row.parent, 0.0) + row.gl_amount
	posted = get_posted_deferred_totals(names, {row.deferred_account for row in rows})
	return {
		name
		for name in names
		if abs(posted.get(name, 0.0) - gross[name]) < abs(posted.get(name, 0.0) - net[name])
	}


def get_item_amount_with_discount_accounting(row, distributed: bool) -> float:
	"""As `get_amount_and_base_amount` (taxes service) plus `_append_item_discount_gl_entries`."""
	amount = flt(row.base_net_amount)
	if row.discount_amount and row.additional_discount_account:
		if not distributed:
			amount = flt(row.base_amount)
		else:
			precision = frappe.get_precision("Sales Invoice Item", "distributed_discount_amount")
			amount += flt(flt(row.distributed_discount_amount) * flt(row.conversion_rate), precision)
	if row.item_discount_amount and row.discount_account:
		precision = frappe.get_precision("Sales Invoice Item", "discount_amount")
		amount += flt(flt(row.item_discount_amount) * flt(row.qty) * flt(row.conversion_rate), precision)
	return amount


def get_invoices_with_distributed_discount(names) -> set:
	"""ERPNext checks the distributed discount on all items of the invoice, not only on the deferred ones."""
	item = frappe.qb.DocType("Sales Invoice Item")
	return set(
		frappe.qb.from_(item)
		.select(item.parent)
		.distinct()
		.where(item.parent.isin(names) & (item.distributed_discount_amount != 0))
		.run(pluck=True)
	)


def get_posted_deferred_totals(names, accounts) -> dict:
	"""The credit less the debit on the deferred accounts, by invoice, without the schedule rows.

	Process Deferred Accounting posts its rows under the voucher number of the invoice.
	"""
	gle = frappe.qb.DocType("GL Entry")
	return dict(
		frappe.qb.from_(gle)
		.select(gle.voucher_no, Sum(gle.credit - gle.debit))
		.where(
			(gle.voucher_type == "Sales Invoice")
			& gle.voucher_no.isin(names)
			& gle.account.isin(accounts)
			& (gle.is_cancelled == 0)
			& (
				gle.against_voucher_type.isnull()
				| (gle.against_voucher_type != "Process Deferred Accounting")
			)
		)
		.groupby(gle.voucher_no)
		.run()
	)


def get_schedule_journal_rows(company: str, invoices: dict, to_date) -> list[dict]:
	"""The GL rows of the Journal Entries of a deferred schedule, against the given invoices.

	invoices: {doctype: names}. "Book Deferred Entries Via Journal Entry" makes these entries.
	"""
	gle = frappe.qb.DocType("GL Entry")
	rows = []
	for doctype, names in invoices.items():
		for batch in batches(sorted(set(names))):
			rows.extend(
				frappe.qb.from_(gle)
				.select(*gl_row_fields(gle))
				.where(
					(gle.company == company)
					& (gle.is_cancelled == 0)
					& (gle.posting_date <= to_date)
					& (gle.voucher_type == "Journal Entry")
					& (gle.voucher_subtype.isin(DEFERRAL_JOURNAL_TYPES))
					& (gle.against_voucher_type == doctype)
					& (gle.against_voucher.isin(batch))
				)
				.orderby(gle.posting_date)
				.orderby(gle.creation)
				.run(as_dict=True)
			)
	return rows


def get_revaluation_journal_entries(company: str, to_date) -> list[str]:
	"""The Exchange Rate Revaluation Journal Entries of the company to the date."""
	journal = frappe.qb.DocType("Journal Entry")
	return (
		frappe.qb.from_(journal)
		.select(journal.name)
		.where(
			(journal.company == company)
			& (journal.docstatus == 1)
			& (journal.voucher_type == "Exchange Rate Revaluation")
			& (journal.posting_date <= to_date)
		)
		.run(pluck=True)
	)


def get_settling_voucher_headers(voucher_type: str, names) -> dict[str, frappe._dict]:
	"""Query 4: the posting dates of the settling Payment Entries and Journal Entries."""
	table = frappe.qb.DocType(voucher_type)
	fields = [table.name, table.posting_date]
	if voucher_type == "Journal Entry":
		fields.extend([table.voucher_type, table.cash_basis_treatment])
	headers = {}
	for batch in batches(sorted(set(names))):
		for row in frappe.qb.from_(table).select(*fields).where(table.name.isin(batch)).run(as_dict=True):
			headers[row.name] = row
	return headers


def batches(values: list, size: int = BATCH_SIZE):
	for start in range(0, len(values), size):
		yield values[start : start + size]
