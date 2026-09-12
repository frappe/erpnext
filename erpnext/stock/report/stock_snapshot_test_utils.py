# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from copy import deepcopy
from datetime import time, timedelta
from unittest.mock import patch

import duckdb
import frappe
import pyarrow as pa
from frappe.database.duckdb.schema import DuckDBTable
from frappe.utils import add_days, today

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import create_stock_reconciliation
from erpnext.stock.report.stock_report_snapshot import StockReportSnapshot
from erpnext.tests.utils import ERPNextTestSuite


class StockSnapshotTestCase(ERPNextTestSuite):
	def setUp(self):
		self.item = make_item("_Test DuckDB Stock Item").name
		self.filters = frappe._dict(
			company="_Test Company",
			item_code=[self.item],
			warehouse=["Stores - _TC"],
			from_date=add_days(today(), -5),
			to_date=today(),
			range="30, 60, 90",
		)

	def assert_snapshot_matches(self, report, **filters):
		report_filters = deepcopy(self.filters)
		report_filters.update(filters)
		expected = report.execute(deepcopy(report_filters))
		actual = self.run_snapshot(report, self.capture_ledger(report_filters.item_code), report_filters)
		self.assertEqual(expected, actual)

	def run_snapshot(self, report, table, filters=None):
		conn = self.connect(table)
		original_sql = frappe.db.sql

		def reject_live_ledger(query, *args, **kwargs):
			self.assertNotIn("tabStock Ledger Entry", str(query))
			return original_sql(query, *args, **kwargs)

		with (
			patch.object(StockReportSnapshot, "get_connection", return_value=conn),
			patch.object(frappe.db, "sql", side_effect=reject_live_ledger),
		):
			return report.execute_snapshot_report(deepcopy(filters or self.filters))

	def capture_ledger(self, items=None):
		rows = frappe.get_all(
			"Stock Ledger Entry",
			filters={"item_code": ("in", items or [self.item])},
			fields=frappe.get_meta("Stock Ledger Entry").get_valid_columns(),
		)
		for row in rows:
			if isinstance(row.posting_time, timedelta):
				seconds = row.posting_time.seconds
				row.posting_time = time(seconds // 3600, seconds % 3600 // 60, seconds % 60)
		return pa.Table.from_pylist(rows, schema=DuckDBTable("Stock Ledger Entry").get_arrow_schema())

	@staticmethod
	def connect(table):
		conn = duckdb.connect(":memory:")
		DuckDBTable("Stock Ledger Entry").sync(conn)
		conn.register("snapshot_data", table)
		source = frappe.qb.Table("snapshot_data")
		query = (
			frappe.qb.into(frappe.qb.DocType("Stock Ledger Entry"))
			.columns(*table.column_names)
			.from_(source)
			.select(*(source[field] for field in table.column_names))
		)
		conn.execute(*StockReportSnapshot.compile(query))
		conn.unregister("snapshot_data")
		return conn

	def make_movement(self, **kwargs):
		args = dict(
			item_code=self.item,
			to_warehouse="Stores - _TC",
			posting_date=today(),
			posting_time="12:00:00",
		)
		args.update(kwargs)
		return make_stock_entry(**args)

	def set_item(self, name, properties):
		self.item = make_item(name, properties).name
		self.filters.item_code = [self.item]

	@property
	def reports(self):
		return (self.report,)

	def make_batch_history(self):
		self.set_item(
			"_Test DuckDB Batch Item",
			{"has_batch_no": 1, "create_new_batch": 1, "batch_number_series": "DUCK-.#####"},
		)
		receipt = self.make_movement(qty=10, basic_rate=100, posting_date=add_days(today(), -10))
		batch = frappe.get_value(
			"Serial and Batch Entry", {"parent": receipt.items[0].serial_and_batch_bundle}, "batch_no"
		)
		self.make_movement(qty=3, batch_no=batch, from_warehouse="Stores - _TC", to_warehouse=None)
		return batch


class StockSnapshotReportMixin:
	def test_spilled_supporting_tables_match(self):
		self.make_movement(qty=10, basic_rate=100, posting_date=add_days(today(), -10))
		self.make_movement(qty=3, from_warehouse="Stores - _TC", to_warehouse=None)
		with patch("erpnext.stock.report.stock_report_snapshot.MAX_LIVE_TABLE_BYTES", 1):
			self.assert_snapshot_matches(self.report)

	def test_snapshot_does_not_read_live_ledger_changes(self):
		self.make_movement(qty=10, basic_rate=100)
		snapshot = self.capture_ledger()
		expected = {report: report.execute(deepcopy(self.filters)) for report in self.reports}
		self.make_movement(qty=5, basic_rate=100)
		for report in self.reports:
			with self.subTest(report=report.__name__):
				self.assertEqual(expected[report], self.run_snapshot(report, snapshot))
				self.assertNotEqual(expected[report][1], report.execute(deepcopy(self.filters))[1])

	def test_stock_reconciliation_matches(self):
		self.make_movement(qty=10, basic_rate=100, posting_date=add_days(today(), -10))
		create_stock_reconciliation(
			item_code=self.item,
			warehouse="Stores - _TC",
			qty=7,
			valuation_rate=120,
			posting_date=add_days(today(), -2),
			posting_time="12:00:00",
		)
		self.make_movement(qty=2, basic_rate=130, posting_date=add_days(today(), -1))
		for report in self.reports:
			with self.subTest(report=report.__name__):
				self.assert_snapshot_matches(report)

	def test_empty_snapshot_preserves_columns(self):
		for report in self.reports:
			with self.subTest(report=report.__name__):
				self.assert_snapshot_matches(report)

	def test_reports_match_with_opening_receipts_and_issues(self):
		self.make_movement(qty=10, basic_rate=100, posting_date=add_days(today(), -10))
		self.make_movement(qty=5, basic_rate=150)
		self.make_movement(qty=3, from_warehouse="Stores - _TC", to_warehouse=None)
		for options in self.receipt_options:
			self.assert_snapshot_matches(self.report, **options)

	def test_filters_and_cancelled_entries_match(self):
		self.make_movement(qty=10, basic_rate=100)
		cancelled = self.make_movement(qty=2, basic_rate=100)
		cancelled.cancel()
		for report in self.reports:
			with self.subTest(report=report.__name__):
				self.assert_snapshot_matches(report)
		parent = frappe.get_value("Warehouse", "Stores - _TC", "parent_warehouse")
		self.assert_snapshot_matches(self.report, warehouse=[parent])
