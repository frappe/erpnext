# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe.query_builder import Case
from frappe.query_builder.functions import IfNull, Sum
from frappe.utils import flt
from pypika.queries import QueryBuilder


class OrderBillingAsOn:
	"""Rebuilds how billing made straight against an order line (no delivery / receipt row on the
	invoice) was spread over that line's delivery / receipt rows on a date, the same way
	update_billed_amount_based_on_so / update_billed_amount_based_on_po spread it today."""

	def __init__(self, doctype: str, links: frappe._dict, as_on_date: str, precision: int):
		self.doctype = doctype
		self.links = links
		self.as_on_date = as_on_date
		self.precision = precision
		self.invoice = frappe.qb.DocType(links.invoice)
		self.invoice_item = frappe.qb.DocType(links.invoice + " Item")

	def get_billed_later(self) -> dict[str, float]:
		"""Part of each row's billed_amt (in company currency) that order-level billing spread on
		it only after the date; negative when the row held more of it on the date."""
		order_lines = self.get_order_lines_billed_after()
		if not order_lines:
			return {}

		billed_against_lines = self.get_billed_against_order_lines(order_lines)
		rows = self.get_rows(order_lines)
		billed_against_rows = self.get_billed_against_rows([row.name for row in rows])

		billed_later = {}
		for order_line, line_rows in group_by_order_line(rows).items():
			billed = billed_against_lines.get(order_line, frappe._dict())
			billed_later.update(self.get_line_billed_later(line_rows, billed, billed_against_rows))
		return billed_later

	def get_line_billed_later(
		self, rows: list[frappe._dict], billed: frappe._dict, billed_against_rows: dict
	) -> dict[str, float]:
		today = self.spread(rows, billed.amount, billed.qty, billed_against_rows, "amount")
		then = self.spread(rows, billed.amount_then, billed.qty_then, billed_against_rows, "amount_then")
		billed_later = {}
		for row in rows:
			if difference := flt(today[row.name] - then[row.name], self.precision):
				billed_later[row.name] = difference * flt(row.conversion_rate)
		return billed_later

	def spread(
		self, rows: list, amount: float, qty: float, billed_against_rows: dict, billed_field: str
	) -> dict[str, float]:
		"""Order-level share of each row when `amount` / `qty` were billed against the order line."""
		pool = OrderBillingPool(amount, qty)
		take = pool.take_for_receipt if self.doctype == "Purchase Receipt" else pool.take_for_delivery
		return {
			row.name: take(row, flt(billed_against_rows.get(row.name, {}).get(billed_field))) for row in rows
		}

	def get_order_lines_billed_after(self) -> list[str]:
		invoice, invoice_item = self.invoice, self.invoice_item
		order_link = invoice_item[self.links.invoice_order_link]
		return (
			frappe.qb.from_(invoice_item)
			.inner_join(invoice)
			.on(invoice.name == invoice_item.parent)
			.select(order_link)
			.distinct()
			.where((invoice.docstatus == 1) & (invoice.posting_date > self.as_on_date))
			.where(order_link.isnotnull() & (order_link != ""))
		).run(pluck=True)

	def get_billed_against_order_lines(self, order_lines: list[str]) -> dict[str, frappe._dict]:
		invoice_item = self.invoice_item
		order_link = invoice_item[self.links.invoice_order_link]
		query = (
			self.get_billed_query(order_link)
			.select(Sum(invoice_item.qty).as_("qty"), self.sum_till_date(invoice_item.qty).as_("qty_then"))
			.where(self.invoice.update_stock == 0)
			.where(order_link.isin(order_lines))
			.where(IfNull(invoice_item[self.links.invoice_link], "") == "")
		)
		return {row.detail: row for row in query.run(as_dict=True)}

	def get_billed_against_rows(self, row_names: list[str]) -> dict[str, frappe._dict]:
		if not row_names:
			return {}
		row_link = self.invoice_item[self.links.invoice_link]
		query = self.get_billed_query(row_link).where(row_link.isin(row_names))
		return {row.detail: row for row in query.run(as_dict=True)}

	def get_billed_query(self, link_field) -> QueryBuilder:
		"""Amount billed per `link_field`, in all and up to the date, skipping notes that don't update billing."""
		invoice_item = self.invoice_item
		return (
			frappe.qb.from_(invoice_item)
			.inner_join(self.invoice)
			.on(self.invoice.name == invoice_item.parent)
			.select(
				link_field.as_("detail"),
				Sum(invoice_item.amount).as_("amount"),
				self.sum_till_date(invoice_item.amount).as_("amount_then"),
			)
			.where(self.invoice.docstatus == 1)
			.where((self.invoice.is_return == 0) | (self.invoice[self.links.billing_flag] == 1))
			.groupby(link_field)
		)

	def sum_till_date(self, field) -> Sum:
		return Sum(Case().when(self.invoice.posting_date <= self.as_on_date, field).else_(0))

	def get_rows(self, order_lines: list[str]) -> list[frappe._dict]:
		"""Delivery / receipt rows of the order lines, in the order the billing is spread over them."""
		parent = frappe.qb.DocType(self.doctype)
		child = frappe.qb.DocType(self.doctype + " Item")
		query = (
			frappe.qb.from_(child)
			.inner_join(parent)
			.on(parent.name == child.parent)
			.select(
				child.name,
				child[self.links.order_link].as_("order_detail"),
				child.amount,
				child.qty,
				IfNull(parent.conversion_rate, 1).as_("conversion_rate"),
			)
			.where((parent.docstatus == 1) & (parent.is_return == 0))
			.where(child[self.links.order_link].isin(order_lines))
			.orderby(parent.posting_date, parent.posting_time, parent.name, child.idx)
		)
		if self.links.invoiced_row_link:
			query = query.select(child[self.links.invoiced_row_link].as_("invoiced_row"))
		return query.run(as_dict=True)


class OrderBillingPool:
	"""What is left of the amount (and qty) billed against an order line while handing it out."""

	def __init__(self, amount: float | None, qty: float | None):
		self.amount = flt(amount)
		self.qty = flt(qty)

	def take_for_delivery(self, row: frappe._dict, billed: float) -> float:
		"""Same first in, first out fill as update_billed_amount_based_on_so."""
		if row.invoiced_row:
			self.amount -= flt(row.amount)
			return flt(row.amount)
		if not self.amount or billed >= flt(row.amount):
			return 0
		share = min(flt(row.amount) - billed, self.amount)
		self.amount -= share
		return share

	def take_for_receipt(self, row: frappe._dict, billed: float) -> float:
		"""Same fill as update_billed_amount_based_on_po: by qty at the billed average rate for an
		unbilled receipt smaller than the qty left, else first in, first out by amount."""
		if not self.amount or billed >= flt(row.amount):
			return 0
		if not billed and self.qty > flt(row.qty):
			share = self.amount * flt(row.qty) / self.qty
			self.qty -= flt(row.qty)
		else:
			share = min(flt(row.amount) - billed, self.amount)
			self.qty *= 1 - share / self.amount
		self.amount -= share
		return share


def group_by_order_line(rows: list[frappe._dict]) -> dict[str, list[frappe._dict]]:
	grouped = defaultdict(list)
	for row in rows:
		grouped[row.order_detail].append(row)
	return grouped
