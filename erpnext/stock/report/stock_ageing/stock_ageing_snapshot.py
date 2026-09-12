# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from collections import defaultdict
from datetime import date, datetime
from typing import NamedTuple

import frappe
from frappe.query_builder import Case, CustomFunction, Field
from frappe.query_builder.functions import Abs, Cast, Count, Floor, IfNull, Max, Min, Sum
from pypika.queries import QueryBuilder
from pypika.terms import Star

from erpnext.stock.report.stock_ageing.fifo_snapshot_queries import FIFOLayers
from erpnext.stock.report.stock_ageing.stock_ageing import DETAIL_FIELDS

ArgMin = CustomFunction("arg_min_null", ["value", "order"])
ArgMax = CustomFunction("arg_max_null", ["value", "order"])
Row = CustomFunction("row", ["posting_datetime", "creation"])

FAST_KEYS = "fifo_fast_keys"
# Scaling by a power of two admits exact binary fractions. Keep scaled totals below 2**52
# to leave headroom for intermediate additions and subtractions in the layer calculation.
BINARY_FRACTION_SCALE = 1024
MAX_EXACT_SCALED_SUM = 2**52

StockKey = tuple[str, str | None]


class ReceiptDate(NamedTuple):
	order: tuple[datetime, datetime]
	is_serial: bool
	number: str
	date: date


class SnapshotFIFOResult(NamedTuple):
	"""Aggregated groups and the remaining query for FIFOSlots to replay in ledger order."""

	details: dict[StockKey, dict]
	replay_query: QueryBuilder | None
	ordered_keys: list[StockKey]
	date_events: list[ReceiptDate]
	tracked_keys: list[StockKey]


class SnapshotFIFO(FIFOLayers):
	"""Resolve surviving receipt layers in DuckDB when FIFO arithmetic is exact."""

	def __init__(self, fifo):
		super().__init__()
		self.fifo = fifo
		self.snapshot = fifo.snapshot
		ledger = frappe.qb.DocType("Stock Ledger Entry")
		self.ledger_entries = fifo._get_stock_ledger_query(ordered=False).select(
			ledger.posting_datetime, ledger.creation
		)

	def generate(self, serial_bundles=None, batch_bundles=None) -> SnapshotFIFOResult | None:
		"""Return aggregated groups and optional replay, or None when every entry needs replay."""
		summaries = self.snapshot.run(self.get_summary_query(), as_dict=True)
		if len({row.first_order for row in summaries}) != len(summaries):
			return None
		eligible = [row for row in summaries if self.can_aggregate(row)]
		tracked_layers, date_events = {}, []
		tracked = [row for row in summaries if self.can_aggregate_tracked(row)]
		if tracked:
			from erpnext.stock.report.stock_ageing.stock_ageing_tracked_snapshot import TrackedFIFO

			tracked_layers, date_events = TrackedFIFO(
				self.fifo, self.ledger_entries, serial_bundles or {}, batch_bundles or {}, tracked
			).generate(tracked)
		if summaries and not (eligible or tracked_layers):
			return None

		entries = self.ledger_entries
		if len(eligible) != len(summaries):
			self.register_fast_keys([self.stock_key(row) for row in eligible])
			entries = self.get_fast_entries()

		layers = self.get_surviving_layers(entries) if eligible else {}
		details = {
			self.stock_key(row): self.build_details(row, layers.get(self.stock_key(row), []))
			for row in eligible
		}
		details.update(
			(self.stock_key(row), self.build_details(row, tracked_layers[self.stock_key(row)]))
			for row in summaries
			if self.stock_key(row) in tracked_layers
		)
		replay_query = None
		if len(details) != len(summaries):
			self.register_fast_keys(list(details))
			replay_query = self.get_replay_query(with_order=bool(date_events))
		return SnapshotFIFOResult(
			details,
			replay_query,
			[self.stock_key(row) for row in summaries],
			date_events,
			list(tracked_layers),
		)

	@staticmethod
	def stock_key(row) -> StockKey:
		return (row.name, row.warehouse)

	@staticmethod
	def build_details(row, layers: list) -> dict:
		return {
			"details": frappe._dict({field: row[field] for field in DETAIL_FIELDS}),
			"fifo_queue": layers,
			"total_qty": row.total_qty,
			"qty_after_transaction": row.final_qty,
			"has_serial_no": row.has_serial_no,
			"has_batch_no": row.has_batch_no,
		}

	def register_fast_keys(self, keys: list[StockKey]) -> None:
		"""Publish the aggregated groups to DuckDB so the split needs no parameter per group."""
		rows = [{"name": name, "warehouse": warehouse} for name, warehouse in keys]
		self.snapshot.register(FAST_KEYS, rows, {"name": "string", "warehouse": "string"})

	def get_surviving_layers(self, entries: QueryBuilder) -> dict[StockKey, list]:
		layers = defaultdict(list)
		for item, warehouse, qty, posting_date, value in self.snapshot.run(
			self.get_layers_query(entries), as_iterator=True
		):
			layers[(item, warehouse)].append([qty, posting_date, value])
		return dict(layers)

	def get_fast_entries(self) -> QueryBuilder:
		entries, keys = self.ledger_entries.as_("fifo_scope"), frappe.qb.Table(FAST_KEYS)
		return frappe.qb.from_(entries).join(keys).on(self.same_stock(entries, keys)).select(Star(entries))

	def get_replay_query(self, with_order=False) -> QueryBuilder:
		"""Entries left to the existing replay. Rows without a warehouse never match a key."""
		entries, keys = frappe.qb.Table("fifo_replay"), frappe.qb.Table(FAST_KEYS)
		fields = (*DETAIL_FIELDS, "posting_datetime", "creation") if with_order else DETAIL_FIELDS
		return (
			frappe.qb.with_(self.ledger_entries, "fifo_replay")
			.from_(entries)
			.left_join(keys)
			.on(self.same_stock(entries, keys))
			.select(*(Field(field, table=entries) for field in fields))
			.where(Field("name", table=keys).isnull())
			.orderby(Field("posting_datetime", table=entries), Field("creation", table=entries))
		)

	def can_aggregate(self, row) -> bool:
		return (
			not row.unsupported
			and row.min_balance >= 0
			and row.row_count == row.voucher_count == row.order_count
			and row.qty_bound < MAX_EXACT_SCALED_SUM
			and row.value_bound < MAX_EXACT_SCALED_SUM
			and self.fifo._get_item_valuation_method(row.name) in ("FIFO", "Moving Average")
		)

	@staticmethod
	def can_aggregate_tracked(row) -> bool:
		return (
			(row.has_serial_no or row.has_batch_no)
			and not row.has_reconciliation
			and row.min_balance >= 0
			and row.row_count == row.voucher_count == row.order_count
			and row.qty_bound < MAX_EXACT_SCALED_SUM
		)

	def get_summary_query(self) -> QueryBuilder:
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
			scaled = field * BINARY_FRACTION_SCALE
			unsupported |= field.isnull() | (scaled != Floor(scaled))

		return (
			frappe.qb.with_(self.ledger_entries, "fifo_entries")
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
				Max(Case().when(progress.voucher_type == "Stock Reconciliation", 1).else_(0)).as_(
					"has_reconciliation"
				),
				Min(progress.running_qty).as_("min_balance"),
				Sum(progress.actual_qty).as_("total_qty"),
				Sum(Cast(Abs(progress.actual_qty), "DOUBLE") * BINARY_FRACTION_SCALE).as_("qty_bound"),
				Sum(Cast(Abs(progress.stock_value_difference), "DOUBLE") * BINARY_FRACTION_SCALE).as_(
					"value_bound"
				),
			)
			.groupby(progress.name, progress.warehouse)
			.orderby("first_order")
		)
