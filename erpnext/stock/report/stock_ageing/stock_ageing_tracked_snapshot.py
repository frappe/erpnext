# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from collections import defaultdict

import frappe
from frappe.query_builder import Case, CustomFunction
from frappe.query_builder.functions import Abs, Count, Floor, Function, Max, Min, Sum
from pypika.analytics import Max as WindowMax
from pypika.analytics import Min as WindowMin
from pypika.analytics import Sum as WindowSum

from erpnext.stock.report.stock_ageing.fifo_snapshot_queries import FIFOLayers
from erpnext.stock.report.stock_ageing.tracked_fifo_snapshot_queries import (
	GROUP_FIELDS,
	ORDER_FIELDS,
	TrackedFIFOEntries,
)

ArgMin = CustomFunction("arg_min_null", ["value", "order"])
ArgMax = CustomFunction("arg_max_null", ["value", "order"])
TRACKED_KEYS = "fifo_tracked_keys"


class TrackedFIFO:
	"""Resolve serial membership and batch valuation pools, retaining replay for unsafe histories."""

	def __init__(self, fifo, ledger_entries, serial_bundles, batch_bundles, candidates):
		self.snapshot = fifo.snapshot
		self.entries = TrackedFIFOEntries(fifo, ledger_entries, serial_bundles, batch_bundles, candidates)
		self.layers = FIFOLayers(GROUP_FIELDS, ORDER_FIELDS, ("tracking_no", "batchwise"))

	def generate(self, summaries):
		from erpnext.stock.report.stock_ageing.stock_ageing_snapshot import ReceiptDate

		queues, date_events = {}, []
		for serial in (True, False):
			expected = {
				(row.name, row.warehouse): row
				for row in summaries
				if bool(row.has_serial_no) == serial and (serial or row.has_batch_no)
			}
			if not expected:
				continue
			query = self.entries.get_query(serial)
			self.snapshot.register_query("fifo_tracked_events", query)
			events = frappe.qb.Table("fifo_tracked_events")
			query = frappe.qb.from_(events).select(events.star)
			keys = [
				(row.name, row.warehouse)
				for row in self.snapshot.run(self.get_summary_query(query, serial), as_dict=True)
				if self.can_aggregate(row, expected.get((row.name, row.warehouse)), serial)
			]
			if not keys:
				continue
			query = self.select_groups(query, keys)
			layers = self.get_serial_layers(query) if serial else self.get_batch_layers(query)
			queues.update({key: layers.get(key, []) for key in keys})
			date_events.extend(
				ReceiptDate(order, serial, number, date)
				for order, number, date in self.snapshot.run(self.get_dates_query(query))
			)
		return queues, sorted(date_events)

	@staticmethod
	def can_aggregate(row, expected, serial):
		from erpnext.stock.report.stock_ageing.stock_ageing_snapshot import MAX_EXACT_SCALED_SUM

		return (
			expected is not None
			and expected.warehouse is not None
			and expected.row_count == expected.voucher_count == expected.order_count == row.row_count
			and not row.unsupported
			and row.min_balance >= 0
			and (not serial or row.max_balance <= 1)
			and row.qty_bound < MAX_EXACT_SCALED_SUM
			and (serial or row.value_bound < MAX_EXACT_SCALED_SUM)
		)

	def get_summary_query(self, query, serial):
		from erpnext.stock.report.stock_ageing.stock_ageing_snapshot import BINARY_FRACTION_SCALE

		events = query.as_("tracked_events")
		progress_query = frappe.qb.from_(events).select(
			events.star,
			self.layers.running_sum(events.actual_qty, events).as_("pool_qty"),
			WindowSum(Abs(events.actual_qty))
			.over(events.name, events.warehouse, events.posting_datetime, events.creation)
			.as_("row_qty"),
		)
		if not serial:
			batchwise = Case().when(events.batchwise != 0, 1).else_(0)
			progress_query = progress_query.select(
				WindowMin(batchwise)
				.over(events.name, events.warehouse, events.tracking_no)
				.as_("min_batchwise"),
				WindowMax(batchwise)
				.over(events.name, events.warehouse, events.tracking_no)
				.as_("max_batchwise"),
			)
		progress = progress_query.as_("tracked_progress")
		unsupported = (
			(progress.voucher_type == "Stock Reconciliation")
			| (progress.order_multiplicity != 1)
			| (progress.row_qty != Abs(progress.source_qty))
			| (progress.source_qty == 0)
			| (progress.text_supported == 0)
			| progress.creation.isnull()
		)
		for field in (progress.actual_qty, progress.stock_value_difference):
			unsupported |= field.isnull()
			if not serial:
				unsupported |= field * BINARY_FRACTION_SCALE != Floor(field * BINARY_FRACTION_SCALE)
		if serial:
			unsupported |= progress.source_balance.isnull() | (
				progress.source_balance != progress.running_qty
			)
		else:
			unsupported |= (
				(progress.actual_qty == 0)
				| (progress.has_legacy_serial != 0)
				| (progress.min_batchwise != progress.max_batchwise)
			)

		return (
			frappe.qb.from_(progress)
			.select(
				progress.name,
				progress.warehouse,
				Count(Function("row", progress.posting_datetime, progress.creation))
				.distinct()
				.as_("row_count"),
				Max(Case().when(unsupported, 1).else_(0)).as_("unsupported"),
				Min(progress.pool_qty).as_("min_balance"),
				Max(progress.pool_qty).as_("max_balance"),
				Sum(Abs(progress.actual_qty) * BINARY_FRACTION_SCALE).as_("qty_bound"),
				Sum(Abs(progress.stock_value_difference) * BINARY_FRACTION_SCALE).as_("value_bound"),
			)
			.groupby(progress.name, progress.warehouse)
		)

	def select_groups(self, query, keys):
		self.snapshot.register(
			TRACKED_KEYS,
			[{"name": name, "warehouse": warehouse} for name, warehouse in keys],
			{"name": "string", "warehouse": "string"},
		)
		events, groups = query.as_("tracked_events"), frappe.qb.Table(TRACKED_KEYS)
		return (
			frappe.qb.from_(events)
			.join(groups)
			.on(FIFOLayers().same_stock(events, groups))
			.select(events.star)
		)

	def get_serial_layers(self, query):
		events = query.as_("serial_events")
		order = Function("row", *(events[field] for field in ORDER_FIELDS))
		query = (
			frappe.qb.from_(events)
			.select(
				events.name,
				events.warehouse,
				events.tracking_no,
				ArgMax(events.posting_date, order),
				ArgMax(events.stock_value_difference, order),
			)
			.groupby(events.name, events.warehouse, events.tracking_no)
			.having(Sum(events.actual_qty) == 1)
			.orderby(Max(order))
		)
		layers = defaultdict(list)
		for name, warehouse, number, date, value in self.snapshot.run(query):
			layers[(name, warehouse)].append([number, date, value])
		return layers

	def get_batch_layers(self, query):
		layers = defaultdict(list)
		for name, warehouse, _pool, qty, date, value, number, batchwise in self.snapshot.run(
			self.layers.get_layers_query(query)
		):
			layers[(name, warehouse)].append([number, batchwise, qty, date, value])
		return layers

	@staticmethod
	def get_dates_query(query):
		events = query.as_("receipt_dates")
		order = Function("row", events.posting_datetime, events.creation)
		return (
			frappe.qb.from_(events)
			.select(Min(order), events.tracking_no, ArgMin(events.posting_date, order))
			.where(events.actual_qty > 0)
			.groupby(events.tracking_no)
		)
