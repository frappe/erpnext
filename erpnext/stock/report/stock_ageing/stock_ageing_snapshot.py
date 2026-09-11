# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.query_builder.functions import Abs, Cast, Count, Floor, IfNull, Max, Min, Sum
from pypika import Case, CustomFunction, Field
from pypika.analytics import CURRENT_ROW, Preceding
from pypika.analytics import Sum as WindowSum
from pypika.terms import Star

ArgMin = CustomFunction("arg_min_null", ["value", "order"])
ArgMax = CustomFunction("arg_max_null", ["value", "order"])
Row = CustomFunction("row", ["posting_datetime", "creation"])
Least = CustomFunction("least", ["left", "right"])

FAST_KEYS = "fifo_fast_keys"


class SnapshotFIFO:
	"""Resolve surviving receipt layers in DuckDB when FIFO arithmetic is exact."""

	def __init__(self, fifo):
		self.fifo = fifo
		self.snapshot = fifo.snapshot
		ledger = frappe.qb.DocType("Stock Ledger Entry")
		self.ledger_entries = fifo._get_stock_ledger_query(ordered=False).select(
			ledger.posting_datetime, ledger.creation
		)
		self.entries = self.ledger_entries

	def generate(self, serial_bundles=None, batch_bundles=None):
		summaries = self.snapshot.run(self.get_summary_query(), as_dict=True)
		if len({row.first_order for row in summaries}) != len(summaries):
			return None
		eligible = [row for row in summaries if self.can_aggregate(row)]
		if summaries and not eligible:
			return None

		details = {self.stock_key(row): self.build_details(row) for row in eligible}
		replayed = len(eligible) != len(summaries)
		if replayed:
			self.narrow_entries_to(details)
		if details:
			self.add_surviving_layers(details)
		if replayed:
			self.replay_remaining_entries(details, serial_bundles or {}, batch_bundles or {})

		ordered_keys = [self.stock_key(row) for row in summaries]
		return {key: details[key] for key in ordered_keys}

	@staticmethod
	def stock_key(row):
		return (row.name, row.warehouse)

	@staticmethod
	def build_details(row):
		return {
			"details": frappe._dict({field: row[field] for field in DETAIL_FIELDS}),
			"fifo_queue": [],
			"total_qty": row.total_qty,
			"qty_after_transaction": row.final_qty,
			"has_serial_no": row.has_serial_no,
			"has_batch_no": row.has_batch_no,
		}

	def narrow_entries_to(self, details):
		"""Publish the aggregated groups to DuckDB and scope the entry queries to them, so the
		split needs no parameter per group. Must run before the layer query is built."""
		rows = [{"name": name, "warehouse": warehouse} for name, warehouse in details]
		self.snapshot.register(FAST_KEYS, rows, {"name": "string", "warehouse": "string"})
		self.entries = self.get_fast_entries()

	def add_surviving_layers(self, details):
		for item, warehouse, qty, posting_date, value in self.snapshot.run(
			self.get_layers_query(), as_iterator=True
		):
			details[(item, warehouse)]["fifo_queue"].append([qty, posting_date, value])

	def replay_remaining_entries(self, details, serial_bundles, batch_bundles):
		"""Replay the groups DuckDB did not aggregate into the same details, so they keep the
		layers attached above."""
		self.fifo.item_details = details
		for row in self.snapshot.run(self.get_replay_query(), as_dict=True, as_iterator=True):
			self.fifo._process_stock_ledger_entry(row, serial_bundles, batch_bundles)

	def get_fast_entries(self):
		entries, keys = self.ledger_entries.as_("fifo_scope"), frappe.qb.Table(FAST_KEYS)
		return frappe.qb.from_(entries).join(keys).on(self.same_stock(entries, keys)).select(Star(entries))

	def get_replay_query(self):
		"""Entries left to the existing replay. Rows without a warehouse never match a key."""
		entries, keys = frappe.qb.Table("fifo_replay"), frappe.qb.Table(FAST_KEYS)
		return (
			frappe.qb.with_(self.ledger_entries, "fifo_replay")
			.from_(entries)
			.left_join(keys)
			.on(self.same_stock(entries, keys))
			.select(*(Field(field, table=entries) for field in DETAIL_FIELDS))
			.where(Field("name", table=keys).isnull())
			.orderby(Field("posting_datetime", table=entries), Field("creation", table=entries))
		)

	def can_aggregate(self, row):
		return (
			not row.unsupported
			and row.min_balance >= 0
			and row.row_count == row.voucher_count == row.order_count
			and row.qty_bound < 2**52
			and row.value_bound < 2**52
			and self.fifo._get_item_valuation_method(row.name) in ("FIFO", "Moving Average")
		)

	def get_summary_query(self):
		entries = frappe.qb.Table("fifo_entries")
		progress = frappe.qb.Table("fifo_progress")
		order = Row(progress.posting_datetime, progress.creation)
		progress_query = frappe.qb.from_(entries).select(
			entries.star, self.running_sum(entries.actual_qty, entries).as_("running_qty")
		)
		unsupported = (
			(progress.voucher_type == "Stock Reconciliation")
			| (IfNull(progress.has_serial_no, 0) != 0)
			| (IfNull(progress.has_batch_no, 0) != 0)
		)
		for field in ("serial_no", "batch_no", "serial_and_batch_bundle"):
			unsupported |= IfNull(progress[field], "") != ""
		unsupported |= progress.warehouse.isnull() | progress.creation.isnull()
		# Restrict reassociation to exactly representable binary fractions with bounded sums.
		for field in (progress.actual_qty, progress.stock_value_difference):
			unsupported |= field.isnull() | (field * 1024 != Floor(field * 1024))

		return (
			frappe.qb.with_(self.entries, "fifo_entries")
			.with_(progress_query, "fifo_progress")
			.from_(progress)
			.select(
				progress.name,
				progress.warehouse,
				*[
					ArgMin(progress[field], order).as_(field)
					for field in DETAIL_FIELDS
					if field not in ("name", "warehouse", "valuation_rate")
				],
				ArgMax(progress.valuation_rate, order).as_("valuation_rate"),
				ArgMax(progress.qty_after_transaction, order).as_("final_qty"),
				Min(order).as_("first_order"),
				Count("*").as_("row_count"),
				Count(progress.voucher_no).distinct().as_("voucher_count"),
				Count(order).distinct().as_("order_count"),
				Max(Case().when(unsupported, 1).else_(0)).as_("unsupported"),
				Min(progress.running_qty).as_("min_balance"),
				Sum(progress.actual_qty).as_("total_qty"),
				Sum(Cast(Abs(progress.actual_qty), "DOUBLE") * 1024).as_("qty_bound"),
				Sum(Cast(Abs(progress.stock_value_difference), "DOUBLE") * 1024).as_("value_bound"),
			)
			.groupby(progress.name, progress.warehouse)
			.orderby("first_order")
		)

	def get_layers_query(self):
		entries = frappe.qb.Table("fifo_entries")
		progress = frappe.qb.Table("fifo_progress")
		receipts = frappe.qb.Table("fifo_receipts")
		issues = frappe.qb.Table("fifo_issues")
		totals = frappe.qb.Table("fifo_totals")
		resets = frappe.qb.Table("fifo_resets")
		progress_query = frappe.qb.from_(entries).select(
			entries.name,
			entries.warehouse,
			entries.actual_qty,
			entries.stock_value_difference,
			entries.posting_date,
			entries.posting_datetime,
			entries.creation,
			*self.get_cumulative_columns(entries),
		)
		totals_query = (
			frappe.qb.from_(progress)
			.select(
				progress.name,
				progress.warehouse,
				Max(progress.out_qty).as_("out_qty"),
				Max(progress.out_value).as_("out_value"),
			)
			.groupby(progress.name, progress.warehouse)
		)
		# Exact layer exhaustion discards the issue's residual value in the existing FIFO replay.
		resets_query = (
			frappe.qb.from_(issues)
			.join(receipts)
			.on(self.same_stock(issues, receipts) & (issues.out_qty == receipts.in_qty))
			.select(
				issues.name,
				issues.warehouse,
				ArgMax(issues.out_value - receipts.in_value, issues.out_qty).as_("correction"),
			)
			.groupby(issues.name, issues.warehouse)
		)
		return (
			frappe.qb.with_(self.entries, "fifo_entries")
			.with_(progress_query, "fifo_progress")
			.with_(
				frappe.qb.from_(progress).select(progress.star).where(progress.actual_qty > 0),
				"fifo_receipts",
			)
			.with_(
				frappe.qb.from_(progress).select(progress.star).where(progress.actual_qty < 0), "fifo_issues"
			)
			.with_(totals_query, "fifo_totals")
			.with_(resets_query, "fifo_resets")
			.from_(receipts)
			.join(totals)
			.on(self.same_stock(receipts, totals))
			.left_join(resets)
			.on(self.same_stock(receipts, resets))
			.select(
				receipts.name,
				receipts.warehouse,
				Least(receipts.actual_qty, receipts.in_qty - totals.out_qty).as_("qty"),
				receipts.posting_date,
				Case()
				.when(
					receipts.in_qty - receipts.actual_qty < totals.out_qty,
					receipts.in_value - totals.out_value + IfNull(resets.correction, 0),
				)
				.else_(receipts.stock_value_difference)
				.as_("value"),
			)
			.where(receipts.in_qty > totals.out_qty)
			.orderby(receipts.name, receipts.warehouse, receipts.posting_datetime, receipts.creation)
		)

	def get_cumulative_columns(self, entries):
		for field, condition, value in (
			("in_qty", entries.actual_qty > 0, entries.actual_qty),
			("in_value", entries.actual_qty > 0, entries.stock_value_difference),
			("out_qty", entries.actual_qty < 0, -entries.actual_qty),
			("out_value", entries.actual_qty < 0, Abs(entries.stock_value_difference)),
		):
			yield self.running_sum(Case().when(condition, value).else_(0), entries).as_(field)

	@staticmethod
	def running_sum(value, table):
		return (
			WindowSum(value)
			.over(table.name, table.warehouse)
			.orderby(table.posting_datetime, table.creation)
			.rows(Preceding(), CURRENT_ROW)
		)

	@staticmethod
	def same_stock(left, right):
		return (Field("name", table=left) == Field("name", table=right)) & (
			Field("warehouse", table=left) == Field("warehouse", table=right)
		)


DETAIL_FIELDS = (
	"name",
	"item_name",
	"item_group",
	"brand",
	"description",
	"stock_uom",
	"has_batch_no",
	"has_serial_no",
	"actual_qty",
	"stock_value_difference",
	"valuation_rate",
	"posting_date",
	"voucher_type",
	"voucher_no",
	"voucher_detail_no",
	"serial_no",
	"batch_no",
	"qty_after_transaction",
	"serial_and_batch_bundle",
	"warehouse",
)
