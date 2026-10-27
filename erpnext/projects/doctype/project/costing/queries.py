# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import qb
from frappe.query_builder.functions import Coalesce, Extract, NullIf, Sum
from frappe.utils import flt
from pypika.enums import DatePart
from pypika.queries import QueryBuilder
from pypika.terms import Term

CONSUMPTION_VOUCHER_TYPES = ("Stock Entry", "Delivery Note", "Sales Invoice")

# Receipt rows that carry capitalised landed cost, and the document each one belongs to.
LANDED_COST_RECEIPTS = {
	"Purchase Receipt Item": "Purchase Receipt",
	"Purchase Invoice Item": "Purchase Invoice",
	"Subcontracting Receipt Item": "Subcontracting Receipt",
	"Stock Entry Detail": "Stock Entry",
}

MonthlyAmounts = dict[str, float]


class ProjectCostQueries:
	"""A project's cost and billing, worked out from the documents booked against it, as a total or
	by month.

	The rules match the ones the Project uses for the totals it stores (see `Project.update_costing`
	and HRMS's override of it), so the two agree; a test checks that they do. A month is keyed
	"YYYY-MM" and taken from the posting date of the document that booked the amount.
	"""

	def __init__(self, project: str, readable_only: bool = False):
		"""With `readable_only`, the time log, purchase and stock queries keep to the documents the
		user may read, as their list views do. Totals leave it off: they count every document."""
		self.project = project
		self.readable_only = readable_only

	def labour_cost(self, by_month: bool = False) -> float | MonthlyAmounts:
		"""Costing amount of the project's submitted time logs, by the day the work started."""
		detail = qb.DocType("Timesheet Detail")
		return sum_amount(self.time_logs(), detail.base_costing_amount, detail.from_time, by_month)

	def labour_hours(self, by_month: bool = False) -> float | MonthlyAmounts:
		"""Hours on the project's submitted time logs, by the day the work started."""
		detail = qb.DocType("Timesheet Detail")
		return sum_amount(self.time_logs(), detail.hours, detail.from_time, by_month)

	def purchase_cost(self, by_month: bool = False) -> float | MonthlyAmounts:
		"""Non-stock items bought for the project, less the landed cost capitalised into stock.

		Stock items count once they are consumed, in `material_cost`.
		"""
		return combine(
			self.non_stock_purchase_cost(by_month), self.capitalised_landed_cost(by_month), sign=-1
		)

	def material_cost(self, by_month: bool = False) -> float | MonthlyAmounts:
		"""Stock consumed against the project, plus costs capitalised on its stock entries."""
		return combine(self.stock_value_consumed(by_month), self.stock_entry_capitalised_cost(by_month))

	def billed_amount(self, by_month: bool = False) -> float | MonthlyAmounts:
		"""Net amount of submitted Sales Invoice items for the project, returns included."""
		invoice = qb.DocType("Sales Invoice")
		item = qb.DocType("Sales Invoice Item")
		from_invoice, from_item = self.billed_items()
		return combine(
			sum_amount(from_invoice, item.base_net_amount, invoice.posting_date, by_month),
			sum_amount(from_item, item.base_net_amount, invoice.posting_date, by_month),
		)

	def expense_claim_cost(self, by_month: bool = False) -> float | MonthlyAmounts:
		"""Sanctioned amount of submitted Expense Claims for the project, as HRMS adds it to the gross
		margin. Only call it when HRMS is installed."""
		claim = qb.DocType("Expense Claim")
		detail = qb.DocType("Expense Claim Detail")
		return sum_amount(self.expense_claim_rows(), detail.sanctioned_amount, claim.posting_date, by_month)

	def sales_order_amount(self) -> float:
		"""Net total of the submitted Sales Orders that name the project."""
		order = qb.DocType("Sales Order")
		query = qb.from_(order).where((order.project == self.project) & (order.docstatus == 1))
		return sum_amount(query, order.base_net_total)

	def time_logs(self) -> QueryBuilder:
		detail = qb.DocType("Timesheet Detail")
		query = qb.from_(detail).where((detail.project == self.project) & (detail.docstatus == 1))
		return self.keep_readable(query, detail.parent, "Timesheet")

	def non_stock_purchase_cost(self, by_month: bool) -> float | MonthlyAmounts:
		invoice = qb.DocType("Purchase Invoice")
		invoice_item = qb.DocType("Purchase Invoice Item")
		query = self.non_stock_purchase_items()
		return sum_amount(query, invoice_item.base_net_amount, invoice.posting_date, by_month)

	def non_stock_purchase_items(self) -> QueryBuilder:
		"""Purchase invoice items that never enter stock: non-stock and drop-shipped items, unless
		they were bought on a subcontracting order."""
		invoice = qb.DocType("Purchase Invoice")
		invoice_item = qb.DocType("Purchase Invoice Item")
		item = qb.DocType("Item")
		purchase_order = qb.DocType("Purchase Order")
		never_stocked = (
			item.is_stock_item.isnull()
			| (item.is_stock_item == 0)
			| (invoice_item.delivered_by_supplier == 1)
		)
		not_subcontracted = purchase_order.is_subcontracted.isnull() | (purchase_order.is_subcontracted == 0)
		query = (
			qb.from_(invoice_item)
			.join(invoice)
			.on(invoice.name == invoice_item.parent)
			.left_join(item)
			.on(item.name == invoice_item.item_code)
			.left_join(purchase_order)
			.on(purchase_order.name == invoice_item.purchase_order)
			.where((invoice_item.project == self.project) & (invoice_item.docstatus == 1))
			.where(never_stocked & not_subcontracted)
		)
		return self.keep_readable(query, invoice.name, "Purchase Invoice")

	def capitalised_landed_cost(self, by_month: bool) -> float | MonthlyAmounts:
		total = {} if by_month else 0.0
		for row_doctype, parent_doctype in LANDED_COST_RECEIPTS.items():
			row = qb.DocType(row_doctype)
			parent = qb.DocType(parent_doctype)
			query = (
				qb.from_(row)
				.join(parent)
				.on(parent.name == row.parent)
				.where((row.project == self.project) & (row.docstatus == 1))
			)
			total = combine(
				total, sum_amount(query, row.landed_cost_voucher_amount, parent.posting_date, by_month)
			)
		return total

	def stock_value_consumed(self, by_month: bool) -> float | MonthlyAmounts:
		ledger = qb.DocType("Stock Ledger Entry")
		query = self.stock_consumption_entries()
		return sum_amount(query, ledger.stock_value_difference * -1, ledger.posting_date, by_month)

	def stock_consumption_entries(self) -> QueryBuilder:
		"""Stock ledger entries where stock left the warehouse for the project, received stock excluded."""
		ledger = qb.DocType("Stock Ledger Entry")
		stock_entry = qb.DocType("Stock Entry")
		query = (
			qb.from_(ledger)
			.left_join(stock_entry)
			.on((ledger.voucher_type == "Stock Entry") & (stock_entry.name == ledger.voucher_no))
			.where(
				(ledger.project == self.project)
				& (ledger.is_cancelled == 0)
				& ledger.voucher_type.isin(CONSUMPTION_VOUCHER_TYPES)
				& (stock_entry.purpose.isnull() | (stock_entry.purpose != "Material Receipt"))
			)
		)
		return self.keep_readable(query, ledger.name, "Stock Ledger Entry")

	def stock_entry_capitalised_cost(self, by_month: bool) -> float | MonthlyAmounts:
		stock_entry = qb.DocType("Stock Entry")
		row = qb.DocType("Stock Entry Detail")
		query = (
			qb.from_(row)
			.join(stock_entry)
			.on(stock_entry.name == row.parent)
			.where(
				(row.project == self.project)
				& (stock_entry.docstatus == 1)
				& (stock_entry.purpose != "Material Receipt")
			)
		)
		amount = row.additional_cost + row.landed_cost_voucher_amount
		return sum_amount(query, amount, stock_entry.posting_date, by_month)

	def billed_items(self) -> tuple[QueryBuilder, QueryBuilder]:
		"""Submitted Sales Invoice items billed to the project, in two parts: items that leave the
		project empty and take their invoice's, and items that name the project themselves."""
		invoice = qb.DocType("Sales Invoice")
		item = qb.DocType("Sales Invoice Item")
		items = qb.from_(item).join(invoice).on(invoice.name == item.parent)
		from_invoice = items.where(
			item.project.isnull() & (invoice.project == self.project) & (invoice.docstatus == 1)
		)
		from_item = items.where((item.project == self.project) & (item.docstatus == 1))
		return from_invoice, from_item

	def expense_claim_rows(self) -> QueryBuilder:
		"""Submitted Expense Claim rows for the project: a row names it, or leaves it empty and takes the claim's."""
		claim = qb.DocType("Expense Claim")
		detail = qb.DocType("Expense Claim Detail")
		return (
			qb.from_(detail)
			.join(claim)
			.on(claim.name == detail.parent)
			.where(
				(claim.docstatus == 1) & (Coalesce(NullIf(detail.project, ""), claim.project) == self.project)
			)
		)

	def keep_readable(self, query: QueryBuilder, document: Term, doctype: str) -> QueryBuilder:
		"""Limit `query` to the `doctype` documents the user may read, when built with `readable_only`.

		The rules come from the framework's query builder, so User Permissions, owner-only roles and
		permission query hooks all apply."""
		if not self.readable_only:
			return query
		readable = frappe.qb.get_query(doctype, fields=["name"], ignore_permissions=False)
		return query.where(document.isin(readable))


def sum_by(query: QueryBuilder, group: Term, amount: Term) -> dict[str, float]:
	"""Sum `amount` over `query` for each value of `group`."""
	rows = query.select(group.as_("group_value"), Sum(amount).as_("amount")).groupby(group).run(as_dict=True)
	return {row.group_value: flt(row.amount) for row in rows}


def sum_amount(
	query: QueryBuilder, amount: Term, posting_date: Term | None = None, by_month: bool = False
) -> float | MonthlyAmounts:
	"""Sum `amount` over `query`, as one total or by the month of `posting_date`."""
	if not by_month:
		return flt(query.select(Sum(amount)).run()[0][0])

	year = Extract(DatePart.year, posting_date)
	month = Extract(DatePart.month, posting_date)
	rows = (
		query.select(year.as_("year"), month.as_("month"), Sum(amount).as_("amount"))
		.groupby(year, month)
		.run(as_dict=True)
	)
	return {f"{int(row.year):04d}-{int(row.month):02d}": flt(row.amount) for row in rows}


def combine(
	first: float | MonthlyAmounts, second: float | MonthlyAmounts, sign: int = 1
) -> float | MonthlyAmounts:
	"""Add `second` to `first`, or subtract it when `sign` is -1, as totals or month by month."""
	if not isinstance(first, dict):
		return first + sign * second

	months = dict(first)
	for key, amount in second.items():
		months[key] = months.get(key, 0.0) + sign * amount
	return months
