# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from contextlib import contextmanager
from copy import deepcopy
from datetime import time, timedelta
from unittest.mock import Mock, patch

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
		filters = deepcopy(filters or self.filters)
		with snapshot_of(table, self.capture_bundles(filters.item_code)):
			return report.execute_snapshot_report(filters)

	@staticmethod
	def serve(conn):
		"""Serve one in-memory database as both the ledger sync and the bundle sync."""
		return patch.multiple(
			StockReportSnapshot,
			get_connection=Mock(return_value=conn),
			get_synced_connection=Mock(side_effect=lambda doctype: conn.cursor()),
		)

	def capture_ledger(self, items=None):
		return capture("Stock Ledger Entry", {"item_code": ("in", items or [self.item])})

	def capture_bundles(self, items=None):
		return captured_bundles({"item_code": ("in", items or [self.item])})

	@staticmethod
	def connect(table, bundles=None):
		"""An in-memory database holding the ledger and, when given, the bundle tables."""
		conn = duckdb.connect(":memory:")
		tables = {
			"Stock Ledger Entry": table,
			"Serial and Batch Bundle": None,
			"Serial and Batch Entry": None,
		}
		tables.update(bundles or {})
		for doctype, rows in tables.items():
			DuckDBTable(doctype).sync(conn)
			if rows is not None:
				load_rows(conn, doctype, rows)
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

	def make_serial_history(self):
		"""A receipt whose bundle lists its serials in reverse of their creation order."""
		self.set_item("_Test DuckDB Serial Item", {"has_serial_no": 1, "serial_no_series": "DUCK-SN-.#####"})
		receipt = self.make_movement(qty=3, basic_rate=100)
		entries = frappe.get_all(
			"Serial and Batch Entry",
			filters={"parent": receipt.items[0].serial_and_batch_bundle},
			fields=["name", "serial_no"],
			order_by="idx",
		)
		serials = [entry.serial_no for entry in entries]
		for entry, serial in zip(entries, reversed(serials), strict=True):
			frappe.db.set_value("Serial and Batch Entry", entry.name, "serial_no", serial)

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


def capture(doctype, filters):
	rows = frappe.get_all(doctype, filters=filters, fields=frappe.get_meta(doctype).get_valid_columns())
	for row in rows:
		for field, value in row.items():
			if isinstance(value, timedelta):
				seconds = value.seconds
				row[field] = time(seconds // 3600, seconds % 3600 // 60, seconds % 60)
	return pa.Table.from_pylist(rows, schema=DuckDBTable(doctype).get_arrow_schema())


def load_rows(conn, doctype, table):
	conn.register("snapshot_data", table)
	source = frappe.qb.Table("snapshot_data")
	query = (
		frappe.qb.into(frappe.qb.DocType(doctype))
		.columns(*table.column_names)
		.from_(source)
		.select(*(source[field] for field in table.column_names))
	)
	conn.execute(*StockReportSnapshot.compile(query))
	conn.unregister("snapshot_data")


@contextmanager
def snapshot_of(table, bundles=None):
	"""Serve the rows as the ledger and bundle syncs and refuse any live query on those tables."""
	conn = StockSnapshotTestCase.connect(table, bundles)
	original_sql = frappe.db.sql

	def guarded_sql(query, *args, **kwargs):
		for name in ("tabStock Ledger Entry", "tabSerial and Batch Bundle", "tabSerial and Batch Entry"):
			if name in str(query):
				raise AssertionError(f"live {name} query during a snapshot run: {query}")
		return original_sql(query, *args, **kwargs)

	with StockSnapshotTestCase.serve(conn), patch.object(frappe.db, "sql", side_effect=guarded_sql):
		yield conn


def ledger_scope(filters):
	if items := filters.get("item_code"):
		return {"item_code": ("in", items if isinstance(items, list | tuple) else [items])}
	if company := filters.get("company"):
		return {"company": company}
	return {}


def captured_ledger(filters):
	"""The ledger rows in the filters' scope, as a snapshot table."""
	return capture("Stock Ledger Entry", ledger_scope(filters))


def captured_bundles(scope):
	"""The bundle and entry rows a bundle sync would hold for the scope."""
	bundles = capture("Serial and Batch Bundle", scope)
	names = bundles.column("name").to_pylist()
	entries = capture("Serial and Batch Entry", {"parent": ("in", names or [""])})
	return {"Serial and Batch Bundle": bundles, "Serial and Batch Entry": entries}


def execute_on_snapshot(report, filters):
	"""Run a report the way the live tests call execute, but from a snapshot of the ledger."""
	with snapshot_of(captured_ledger(filters), captured_bundles(ledger_scope(filters))):
		return report.execute_snapshot_report(deepcopy(filters))


def on_snapshot(live_tests, **replacements):
	"""A copy of a live report test class that runs the report from a DuckDB snapshot instead."""

	def setUp(self):
		for name, replacement in replacements.items():
			patcher = patch(f"{live_tests.__module__}.{name}", replacement)
			patcher.start()
			self.addCleanup(patcher.stop)
		live_tests.setUp(self)

	return type(f"{live_tests.__name__}OnSnapshot", (live_tests,), {"setUp": setUp})


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
