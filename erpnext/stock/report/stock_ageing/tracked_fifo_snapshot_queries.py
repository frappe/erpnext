# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.query_builder import Case, CustomFunction
from frappe.query_builder.functions import Abs, Cast, IfNull, Upper
from pypika.analytics import Count as WindowCount

from erpnext.stock.report.stock_ageing.fifo_snapshot_queries import FIFOLayers
from erpnext.stock.report.stock_report_snapshot import active_snapshot

StringSplit = CustomFunction("string_split", ["value", "separator"])
Replace = CustomFunction("replace", ["value", "old", "new"])
Unnest = CustomFunction("unnest", ["value"])
Subscripts = CustomFunction("generate_subscripts", ["value", "dimension"])
Trim = CustomFunction("trim", ["value", "characters"])
RegexpMatches = CustomFunction("regexp_matches", ["value", "pattern"])

NON_ASCII = "[^\\x00-\\x7f]"
ORDER_FIELDS = ("posting_datetime", "creation", "entry_name", "bundle_index")
GROUP_FIELDS = ("name", "warehouse", "valuation_pool")


class TrackedFIFOEntries:
	"""Expand legacy fields and bundles into ordered serial or batch movements in DuckDB."""

	def __init__(self, fifo, ledger_entries, candidates):
		self.snapshot = active_snapshot()
		self.ledger_entries = ledger_entries
		self.snapshot.register(
			"fifo_tracked_candidates",
			[{"name": row.name, "warehouse": row.warehouse} for row in candidates],
			{"name": "string", "warehouse": "string"},
		)
		source, keys = (
			self.get_ledger_query().as_("tracked_source"),
			frappe.qb.Table("fifo_tracked_candidates"),
		)
		query = (
			frappe.qb.from_(source).join(keys).on(FIFOLayers().same_stock(source, keys)).select(source.star)
		)
		self.snapshot.register_query("fifo_tracked_source", query)
		self.snapshot.register_query("fifo_bundle_entries", self.get_bundle_entries_query())

	def get_query(self, serial):
		ledger = frappe.qb.Table("fifo_tracked_source")
		legacy = self.get_legacy_serial_query(ledger) if serial else self.get_legacy_batch_query(ledger)
		events = (legacy.union_all(self.get_bundle_query(ledger, serial))).as_("tracked_events")
		pool = (
			Cast(events.tracking_no, "VARCHAR")
			if serial
			else Case().when(events.batchwise != 0, events.tracking_no).else_("")
		)
		return (
			frappe.qb.from_(events)
			.select(events.star, pool.as_("valuation_pool"))
			.where(events.tracking_no != "")
		)

	def get_ledger_query(self):
		ledger = self.ledger_entries.as_("tracked_source")
		return frappe.qb.from_(ledger).select(
			*(
				ledger[field]
				for field in (
					"name",
					"warehouse",
					"posting_datetime",
					"creation",
					"entry_name",
					"posting_date",
					"voucher_type",
					"qty_after_transaction",
					"actual_qty",
					"stock_value_difference",
					"has_serial_no",
					"has_batch_no",
					"serial_no",
					"batch_no",
					"serial_and_batch_bundle",
				)
			),
			WindowCount("*")
			.over(ledger.posting_datetime, ledger.creation, ledger.entry_name)
			.as_("order_multiplicity"),
			FIFOLayers().running_sum(Cast(ledger.actual_qty, "DOUBLE"), ledger).as_("running_qty"),
		)

	def get_legacy_serial_query(self, ledger):
		serials = StringSplit(Replace(IfNull(ledger.serial_no, ""), ",", "\n"), "\n")
		return (
			frappe.qb.from_(ledger)
			.select(
				*self.source_fields(ledger, self.legacy_text_supported(ledger)),
				Upper(Trim(Unnest(serials), " \t\n\r\v\f\x1c\x1d\x1e\x1f")).as_("tracking_no"),
				Subscripts(serials, 1).as_("bundle_index"),
				Cast(0, "BIGINT").as_("batchwise"),
				*self.movement_fields(ledger, serial=True),
			)
			.where((ledger.has_serial_no == 1) & (IfNull(ledger.serial_and_batch_bundle, "") == ""))
		)

	def get_legacy_batch_query(self, ledger):
		batch = frappe.qb.DocType("Batch")
		return (
			frappe.qb.from_(ledger)
			.left_join(batch)
			.on(ledger.batch_no == batch.name)
			.select(
				*self.source_fields(ledger, self.legacy_text_supported(ledger)),
				Upper(IfNull(ledger.batch_no, "")).as_("tracking_no"),
				Cast(0, "BIGINT").as_("bundle_index"),
				batch.use_batchwise_valuation.as_("batchwise"),
				*self.movement_fields(ledger, serial=False),
			)
			.where(
				(IfNull(ledger.has_serial_no, 0) == 0)
				& (ledger.has_batch_no == 1)
				& (IfNull(ledger.serial_and_batch_bundle, "") == "")
			)
		)

	def get_bundle_query(self, ledger, serial):
		bundle = frappe.qb.Table("fifo_bundle_entries")
		return (
			frappe.qb.from_(ledger)
			.join(bundle)
			.on((ledger.serial_and_batch_bundle == bundle.parent) & (bundle.is_serial == int(serial)))
			.select(
				*self.source_fields(ledger, bundle.text_supported),
				bundle.tracking_no,
				bundle.bundle_index,
				bundle.batchwise,
				*self.movement_fields(ledger, serial, bundle),
			)
			.where(
				(ledger.has_serial_no == 1)
				if serial
				else ((IfNull(ledger.has_serial_no, 0) == 0) & (ledger.has_batch_no == 1))
			)
		)

	@staticmethod
	def source_fields(ledger, text_supported):
		return [
			ledger.name,
			ledger.warehouse,
			ledger.posting_datetime,
			ledger.creation,
			ledger.entry_name,
			ledger.posting_date,
			ledger.voucher_type,
			ledger.order_multiplicity,
			ledger.qty_after_transaction.as_("source_balance"),
			ledger.running_qty,
			Case().when(IfNull(ledger.serial_no, "") != "", 1).else_(0).as_("has_legacy_serial"),
			text_supported.as_("text_supported"),
			Cast(ledger.actual_qty, "DOUBLE").as_("source_qty"),
		]

	@staticmethod
	def movement_fields(ledger, serial, bundle=None):
		source_qty = Cast(ledger.actual_qty, "DOUBLE")
		source_value = Cast(ledger.stock_value_difference, "DOUBLE")
		if serial:
			qty = Cast(1, "DOUBLE")
			# Use the same two float operands as Python; no sum or reassociation changes the rate.
			value = source_value / source_qty
		else:
			qty = bundle.qty if bundle is not None else Abs(source_qty)
			value = bundle.value if bundle is not None else Abs(source_value)
		return [
			Case().when(source_qty > 0, qty).else_(-qty).as_("actual_qty"),
			Case().when(source_qty > 0, value).else_(-Abs(value)).as_("stock_value_difference"),
		]

	@staticmethod
	def legacy_text_supported(ledger):
		"""Python and DuckDB can uppercase non-ASCII identifiers differently."""
		non_ascii = RegexpMatches(IfNull(ledger.serial_no, ""), NON_ASCII) | RegexpMatches(
			IfNull(ledger.batch_no, ""), NON_ASCII
		)
		return Case().when(non_ascii, 0).else_(1)

	def get_bundle_entries_query(self):
		"""Serial and batch entries of submitted bundles, as the live report reads them."""
		entry = frappe.qb.DocType("Serial and Batch Entry")
		batch = frappe.qb.DocType("Batch")
		serials = (
			frappe.qb.from_(entry)
			.select(*self.bundle_fields(entry, entry.serial_no, Cast(1, "BIGINT"), Cast(0, "BIGINT")))
			.where((entry.docstatus == 1) & entry.serial_no.isnotnull())
		)
		batches = (
			frappe.qb.from_(entry)
			.join(batch)
			.on(entry.batch_no == batch.name)
			.select(
				*self.bundle_fields(entry, entry.batch_no, Cast(0, "BIGINT"), batch.use_batchwise_valuation)
			)
			.where((entry.docstatus == 1) & entry.batch_no.isnotnull())
		)
		return serials.union_all(batches)

	@staticmethod
	def bundle_fields(entry, number, is_serial, batchwise):
		return [
			entry.parent,
			Upper(number).as_("tracking_no"),
			entry.idx.as_("bundle_index"),
			is_serial.as_("is_serial"),
			batchwise.as_("batchwise"),
			Abs(entry.qty).as_("qty"),
			Abs(entry.stock_value_difference).as_("value"),
			Case().when(RegexpMatches(number, NON_ASCII), 0).else_(1).as_("text_supported"),
		]
