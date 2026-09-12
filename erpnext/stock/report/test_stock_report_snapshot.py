# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from pathlib import Path
from unittest.mock import patch

import frappe
import pyarrow.dataset as ds
from frappe.core.doctype.duckdb_sync.duckdb_sync import DuckDBSync
from frappe.query_builder.builder import MariaDB, Postgres
from frappe.query_builder.functions import Cast, Count
from frappe.utils import add_days, today

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import create_stock_reconciliation
from erpnext.stock.report.stock_report_snapshot import StockReportSnapshot
from erpnext.stock.report.stock_snapshot_test_utils import StockSnapshotTestCase


class TestStockReportSnapshot(StockSnapshotTestCase):
	def test_reconciliation_lookup_ignores_other_vouchers(self):
		self.make_movement(qty=10, basic_rate=100, posting_date=add_days(today(), -1))
		conn = self.connect(self.capture_ledger())
		with patch.object(StockReportSnapshot, "get_connection", return_value=conn):
			with StockReportSnapshot("Stock Ledger", self.filters) as snapshot:
				with patch.object(frappe, "get_all", wraps=frappe.get_all) as get_all:
					self.assertEqual(snapshot.get_table("tabStock Reconciliation").num_rows, 0)
					get_all.assert_not_called()

		reconciliation = create_stock_reconciliation(
			item_code=self.item, warehouse="Stores - _TC", qty=7, valuation_rate=100
		)
		conn = self.connect(self.capture_ledger())
		with patch.object(StockReportSnapshot, "get_connection", return_value=conn):
			with StockReportSnapshot("Stock Ledger", self.filters) as snapshot:
				with patch.object(frappe, "get_all", wraps=frappe.get_all) as get_all:
					self.assertEqual(snapshot.get_table("tabStock Reconciliation").num_rows, 1)
					get_all.assert_called_once()
					self.assertEqual(
						get_all.call_args.kwargs["filters"], {"name": ("in", [reconciliation.name])}
					)

	def test_supporting_tables_are_read_in_batches(self):
		items = [self.item, make_item("_Test DuckDB Batched Item").name]
		self.filters.item_code = items
		for item in items:
			self.make_movement(item_code=item, qty=1, basic_rate=100)
		conn = self.connect(self.capture_ledger(items))
		with (
			patch.object(StockReportSnapshot, "get_connection", return_value=conn),
			patch("erpnext.stock.report.stock_report_snapshot.BATCH_SIZE", 1),
			patch.object(frappe, "get_all", wraps=frappe.get_all) as get_all,
		):
			with StockReportSnapshot("Stock Balance", self.filters) as snapshot:
				self.assertEqual(snapshot.get_table("tabItem").num_rows, 2)

		self.assertEqual(get_all.call_count, 2)
		for call in get_all.call_args_list:
			self.assertEqual(len(call.kwargs["filters"]["name"][1]), 1)

	def test_snapshot_result_types_and_nulls(self):
		self.make_movement(qty=1, basic_rate=100.25)
		ledger = frappe.qb.DocType("Stock Ledger Entry")
		query = (
			frappe.qb.from_(ledger)
			.select(
				ledger.incoming_rate,
				ledger.posting_time,
				ledger.posting_date,
				Cast(None, "DECIMAL(21,9)").as_("empty_qty"),
				Cast(None, "TIME").as_("empty_time"),
				ledger.item_code,
			)
			.where(ledger.item_code == self.item)
		)
		expected = [tuple(row) for row in query.run()]
		expected_dicts = query.run(as_dict=True)
		conn = self.connect(self.capture_ledger())
		with patch.object(StockReportSnapshot, "get_connection", return_value=conn):
			with StockReportSnapshot("Stock Ledger", self.filters) as snapshot:
				self.assertEqual(snapshot.run(query), expected)
				self.assertEqual(snapshot.run(query, as_dict=True), expected_dicts)
				self.assertEqual(list(snapshot.run(query, as_iterator=True)), expected)
				self.assertEqual(snapshot.run(query, pluck=True), [100.25])

	def test_large_supporting_table_spills_and_can_be_scanned_repeatedly(self):
		self.set_item("_Test DuckDB Spill Item", {"has_serial_no": 1, "serial_no_series": "DUCK-SP-.#####"})
		self.make_movement(qty=7, basic_rate=100)
		conn = self.connect(self.capture_ledger())
		entries = frappe.qb.DocType("Serial and Batch Entry")
		query = frappe.qb.from_(entries).select(entries.qty, entries.batch_no)
		with (
			patch.object(StockReportSnapshot, "get_connection", return_value=conn),
			patch("erpnext.stock.report.stock_report_snapshot.BATCH_SIZE", 2),
			patch("erpnext.stock.report.stock_report_snapshot.MAX_LIVE_TABLE_BYTES", 1),
			patch.object(frappe.db, "unbuffered_cursor", wraps=frappe.db.unbuffered_cursor) as unbuffered,
		):
			with StockReportSnapshot("Stock Ledger", self.filters) as snapshot:
				table = snapshot.get_table("tabSerial and Batch Entry")
				self.assertIsInstance(table, ds.FileSystemDataset)
				path = Path(table.files[0])
				self.assertTrue(path.exists())
				self.assertEqual([batch.num_rows for batch in table.to_batches()], [2, 2, 2, 1])
				expected = snapshot.run(query)
				self.assertEqual(len(expected), 7)
				self.assertTrue(all(qty == 1 and not batch for qty, batch in expected))
				self.assertEqual(snapshot.run(query), expected)
				other = entries.as_("other")
				join = (
					frappe.qb.from_(entries)
					.inner_join(other)
					.on(entries.parent == other.parent)
					.select(Count(entries.parent))
				)
				self.assertEqual(snapshot.run(join), [(49,)])
				unbuffered.assert_called_once()
		self.assertFalse(path.exists())

	def test_failed_spill_cleans_files_and_restores_live_cursor(self):
		self.make_movement(qty=1, basic_rate=100)
		conn = self.connect(self.capture_ledger())
		original_cursor = frappe.db._cursor
		with (
			patch.object(StockReportSnapshot, "get_connection", return_value=conn),
			patch("erpnext.stock.report.stock_report_snapshot.MAX_LIVE_TABLE_BYTES", 1),
			patch("pyarrow.ipc.new_file", side_effect=OSError("disk full")),
		):
			with self.assertRaisesRegex(OSError, "disk full"):
				with StockReportSnapshot("Stock Ledger", self.filters) as snapshot:
					snapshot.get_table("tabItem")
		self.assertFalse(Path(snapshot.temp_directory.name).exists())
		self.assertIs(frappe.db._cursor, original_cursor)
		self.assertEqual(frappe.db.get_value("Item", self.item), self.item)

	def test_requires_latest_submitted_sync_to_be_complete(self):
		complete = frappe.get_doc(doctype="DuckDB Sync", doc_type="Stock Ledger Entry").insert()
		complete.db_set("docstatus", 1)
		complete.db_tables[0].db_set("synced", 1)
		pending = frappe.get_doc(doctype="DuckDB Sync", doc_type="Stock Ledger Entry").insert()
		pending.db_set("docstatus", 1)
		frappe.get_doc(doctype="DuckDB Sync", doc_type="Stock Ledger Entry").insert()
		with patch.object(DuckDBSync, "get_duckdb_conn", autospec=True, side_effect=lambda doc: doc.name):
			self.assertRaises(frappe.ValidationError, StockReportSnapshot.get_connection, "Stock Ledger")
			pending.db_tables[0].db_set("synced", 1)
			self.assertEqual(StockReportSnapshot.get_connection("Stock Ledger"), pending.name)

	def test_query_parameters_and_dialects(self):
		self.make_movement(qty=1, basic_rate=100)
		table = self.capture_ledger()
		with patch.object(StockReportSnapshot, "get_connection", side_effect=lambda _: self.connect(table)):
			with StockReportSnapshot("Stock Ledger") as snapshot:
				for builder in (MariaDB, Postgres):
					with self.subTest(builder=builder.__name__):
						sle = builder.DocType("Stock Ledger Entry")
						query = builder.from_(sle).select(sle.item_code).where(sle.item_code == self.item)
						self.assertEqual(snapshot.run(query, pluck=True), [self.item])
						query = builder.from_(sle).select(sle.name).where(sle.item_code == "x' OR 1=1 -- `")
						self.assertEqual(snapshot.run(query), [])

	def test_cte_named_after_live_table_does_not_load_that_doctype(self):
		self.make_movement(qty=1, basic_rate=100)
		ledger = frappe.qb.DocType("Stock Ledger Entry")
		item = frappe.qb.DocType("Item")
		entries = frappe.qb.from_(ledger).select(ledger.item_code.as_("name"))
		query = frappe.qb.with_(entries, "tabItem").from_(item).select(item.name)
		conn = self.connect(self.capture_ledger())
		with patch.object(StockReportSnapshot, "get_connection", return_value=conn):
			with StockReportSnapshot("Stock Ledger", self.filters) as snapshot:
				with patch.object(snapshot, "build_live_table") as build_live_table:
					self.assertEqual(snapshot.run(query, pluck=True), [self.item])
					build_live_table.assert_not_called()

	def test_cached_query_preserves_types_and_parameters(self):
		self.make_movement(qty=1, basic_rate=100.25)
		ledger = frappe.qb.DocType("Stock Ledger Entry")
		query = (
			frappe.qb.from_(ledger)
			.select(ledger.item_code, ledger.actual_qty, ledger.posting_time)
			.where(ledger.item_code == self.item)
		)
		with patch.object(
			StockReportSnapshot, "get_connection", return_value=self.connect(self.capture_ledger())
		):
			with StockReportSnapshot("Stock Ledger", self.filters) as snapshot:
				expected = snapshot.run(query)
				snapshot.register_query("cached_movements", query)
				table = frappe.qb.Table("cached_movements")
				self.assertEqual(snapshot.run(frappe.qb.from_(table).select(table.star)), expected)
