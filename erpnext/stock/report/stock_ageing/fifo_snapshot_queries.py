# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.query_builder import Case, Criterion, CustomFunction
from frappe.query_builder.functions import Abs, IfNull, Max
from pypika.analytics import CURRENT_ROW, Preceding
from pypika.analytics import Sum as WindowSum
from pypika.queries import QueryBuilder

ArgMax = CustomFunction("arg_max_null", ["value", "order"])
Least = CustomFunction("least", ["left", "right"])


class FIFOLayers:
	"""Queries for exact FIFO movements, partitioned by stock or a batch valuation pool."""

	def __init__(
		self,
		group_fields=("name", "warehouse"),
		order_fields=("posting_datetime", "creation"),
		receipt_fields=(),
	):
		self.group_fields = group_fields
		self.order_fields = order_fields
		self.receipt_fields = receipt_fields

	def get_layers_query(self, ledger_entries: QueryBuilder) -> QueryBuilder:
		entries = frappe.qb.Table("fifo_entries")
		progress = frappe.qb.Table("fifo_progress")
		receipts = frappe.qb.Table("fifo_receipts")
		issues = frappe.qb.Table("fifo_issues")
		totals = frappe.qb.Table("fifo_totals")
		resets = frappe.qb.Table("fifo_resets")
		return (
			frappe.qb.with_(ledger_entries, "fifo_entries")
			.with_(self.get_progress_query(entries), "fifo_progress")
			.with_(
				frappe.qb.from_(progress).select(progress.star).where(progress.actual_qty > 0),
				"fifo_receipts",
			)
			.with_(
				frappe.qb.from_(progress).select(progress.star).where(progress.actual_qty < 0), "fifo_issues"
			)
			.with_(self.get_totals_query(progress), "fifo_totals")
			.with_(self.get_resets_query(issues, receipts), "fifo_resets")
			.from_(receipts)
			.join(totals)
			.on(self.same_stock(receipts, totals))
			.left_join(resets)
			.on(self.same_stock(receipts, resets))
			.select(
				*(receipts[field] for field in self.group_fields),
				Least(receipts.actual_qty, receipts.in_qty - totals.out_qty).as_("qty"),
				receipts.posting_date,
				Case()
				.when(
					receipts.in_qty - receipts.actual_qty < totals.out_qty,
					receipts.in_value - totals.out_value + IfNull(resets.correction, 0),
				)
				.else_(receipts.stock_value_difference)
				.as_("value"),
				*(receipts[field] for field in self.receipt_fields),
			)
			.where(receipts.in_qty > totals.out_qty)
			.orderby(*(receipts[field] for field in (*self.order_fields, *self.group_fields)))
		)

	def get_progress_query(self, entries) -> QueryBuilder:
		return frappe.qb.from_(entries).select(
			*(entries[field] for field in self.group_fields),
			entries.actual_qty,
			entries.stock_value_difference,
			entries.posting_date,
			*(entries[field] for field in dict.fromkeys((*self.order_fields, *self.receipt_fields))),
			*self.get_cumulative_columns(entries),
		)

	def get_totals_query(self, progress) -> QueryBuilder:
		return (
			frappe.qb.from_(progress)
			.select(
				*(progress[field] for field in self.group_fields),
				Max(progress.out_qty).as_("out_qty"),
				Max(progress.out_value).as_("out_value"),
			)
			.groupby(*(progress[field] for field in self.group_fields))
		)

	def get_resets_query(self, issues, receipts) -> QueryBuilder:
		"""Match replay's discarded residual value when a receipt layer is exhausted.

		For (quantity, value): receive (10, 100), issue (10, 90), receive (5, 50), issue (1, 10).
		The exhausted first layer discards 10 of value, leaving (4, 40) in the second layer.
		"""
		return (
			frappe.qb.from_(issues)
			.join(receipts)
			.on(self.same_stock(issues, receipts) & (issues.out_qty == receipts.in_qty))
			.select(
				*(issues[field] for field in self.group_fields),
				ArgMax(issues.out_value - receipts.in_value, issues.out_qty).as_("correction"),
			)
			.groupby(*(issues[field] for field in self.group_fields))
		)

	def get_cumulative_columns(self, entries):
		for field, condition, value in (
			("in_qty", entries.actual_qty > 0, entries.actual_qty),
			("in_value", entries.actual_qty > 0, entries.stock_value_difference),
			("out_qty", entries.actual_qty < 0, -entries.actual_qty),
			("out_value", entries.actual_qty < 0, Abs(entries.stock_value_difference)),
		):
			yield self.running_sum(Case().when(condition, value).else_(0), entries).as_(field)

	def running_sum(self, value, table):
		return (
			WindowSum(value)
			.over(*(table[field] for field in self.group_fields))
			.orderby(*(table[field] for field in self.order_fields))
			.rows(Preceding(), CURRENT_ROW)
		)

	def same_stock(self, left, right):
		return Criterion.all(left[field] == right[field] for field in self.group_fields)
