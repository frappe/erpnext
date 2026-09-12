# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from copy import deepcopy
from datetime import time, timedelta
from decimal import Decimal
from random import Random
from unittest.mock import patch

import duckdb
import frappe
import pyarrow as pa
from frappe.utils import add_days, today

from erpnext.stock.report.stock_ledger import stock_ledger
from erpnext.stock.report.stock_report_snapshot import StockReportSnapshot
from erpnext.stock.report.stock_snapshot_test_utils import StockSnapshotReportMixin, StockSnapshotTestCase


class TestStockLedgerSnapshotReport(StockSnapshotReportMixin, StockSnapshotTestCase):
	report = stock_ledger
	receipt_options = ({},)

	def test_batch_filter_scopes_serial_and_batch_entries(self):
		self.set_item(
			"_Test DuckDB Scoped Batch Item",
			{"has_batch_no": 1, "create_new_batch": 1, "batch_number_series": "DUCKS-.#####"},
		)
		batches = [
			frappe.get_value(
				"Serial and Batch Entry",
				{
					"parent": self.make_movement(qty=5, basic_rate=100, posting_date=day)
					.items[0]
					.serial_and_batch_bundle
				},
				"batch_no",
			)
			for day in (add_days(today(), -2), add_days(today(), -1))
		]
		filters = deepcopy(self.filters)
		filters.batch_no = batches[0]
		conn = self.connect(self.capture_ledger())
		with patch.object(StockReportSnapshot, "get_connection", return_value=conn):
			with StockReportSnapshot("Stock Ledger", filters) as snapshot:
				entries = snapshot.get_table("tabSerial and Batch Entry")

		self.assertEqual(set(entries.column("batch_no").to_pylist()), {batches[0]})
		self.assert_snapshot_matches(stock_ledger, batch_no=batches[0], segregate_serial_batch_bundle=1)

	def test_ledger_native_conversions_preserve_python_values(self):
		random = Random(42)
		values = [None, Decimal("999999999999.999999999"), Decimal("-0.000000001"), Decimal("0.1")]
		values.extend(Decimal(random.randrange(-(10**21), 10**21)).scaleb(-9) for _ in range(1000))
		times = [None, time(), time(23, 59, 59, 999999), time(12, 30, 45, 123456)] * 251
		table = pa.table(
			{
				"actual_qty": pa.array(values, type=pa.decimal128(21, 9)),
				"posting_time": pa.array(times, type=pa.time64("us")),
			}
		)
		with duckdb.connect(":memory:") as conn:
			conn.register("native_values", table)
			source = frappe.qb.Table("native_values")
			query = frappe.qb.from_(source).select(
				*stock_ledger.get_snapshot_fields([source.actual_qty, source.posting_time])
			)
			actual = conn.execute(*StockReportSnapshot.compile(query)).fetchall()
		expected = [
			(
				float(value) if value is not None else None,
				timedelta(
					hours=clock.hour,
					minutes=clock.minute,
					seconds=clock.second,
					microseconds=clock.microsecond,
				)
				if clock is not None
				else None,
			)
			for value, clock in zip(values, times, strict=True)
		]
		self.assertEqual(actual, expected)

	def test_ledger_aggregates_opening_history_in_duckdb(self):
		from erpnext.stock.report.stock_ledger import stock_ledger_snapshot

		self.make_movement(qty=10, basic_rate=100, posting_date=add_days(today(), -10))
		self.make_movement(qty=3, from_warehouse="Stores - _TC", to_warehouse=None)
		expected = stock_ledger.execute(deepcopy(self.filters))
		with patch.object(
			stock_ledger_snapshot, "get_opening_query", wraps=stock_ledger_snapshot.get_opening_query
		) as prepare:
			self.assertEqual(expected, self.run_snapshot(stock_ledger, self.capture_ledger()))
			prepare.assert_called_once()

	def test_serial_bundle_details_match(self):
		self.set_item("_Test DuckDB Serial Item", {"has_serial_no": 1, "serial_no_series": "DUCK-SN-.#####"})
		self.make_movement(qty=3, basic_rate=100)
		self.assert_snapshot_matches(stock_ledger, segregate_serial_batch_bundle=1)

	def test_batch_opening_and_bundle_details_match(self):
		batch = self.make_batch_history()
		self.assert_snapshot_matches(stock_ledger, batch_no=batch, segregate_serial_batch_bundle=1)

	def test_inventory_dimension_opening_and_grouping_match(self):
		opening = self.make_movement(qty=10, basic_rate=100, posting_date=add_days(today(), -10))
		current = self.make_movement(qty=5, basic_rate=100)
		for entry in (opening, current):
			frappe.db.set_value("Stock Ledger Entry", {"voucher_no": entry.name}, "project", "DuckDB Project")
		dimensions = [frappe._dict(fieldname="project", doctype="Project")]
		with patch.object(stock_ledger, "get_inventory_dimensions", return_value=dimensions):
			self.assert_snapshot_matches(stock_ledger, project=["DuckDB Project"])
