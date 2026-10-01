# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta
from unittest.mock import patch

import duckdb
import frappe
import pyarrow as pa
from frappe.database.duckdb.database import DuckDBConnection
from frappe.database.duckdb.schema import DuckDBTable
from frappe.utils import add_days, now_datetime, today

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import create_stock_reconciliation
from erpnext.stock.report.stock_balance import stock_balance
from erpnext.stock.report.stock_balance import test_stock_balance as live_tests
from erpnext.tests.utils import ERPNextTestSuite

SNAPSHOT = "erpnext.stock.report.stock_balance.stock_balance_snapshot"
LATEST_SYNC = f"{SNAPSHOT}.get_latest_complete_sync"


def capture_ledger(filters):
	"""The ledger rows a sync would hold for the report's items, or for its company."""
	scope = (
		{"item_code": ("in", items)} if (items := filters.get("item_code")) else {"company": filters.company}
	)
	rows = frappe.get_all(
		"Stock Ledger Entry", filters=scope, fields=frappe.get_meta("Stock Ledger Entry").get_valid_columns()
	)
	for row in rows:
		if isinstance(row.posting_time, timedelta):
			row.posting_time = (datetime.min + row.posting_time).time()
	return pa.Table.from_pylist(rows, schema=DuckDBTable("Stock Ledger Entry").get_arrow_schema())


@contextmanager
def ledger_snapshot(table, synced_at=None):
	"""Serve the rows as the latest sync and fail on any live ledger query meanwhile."""
	conn = duckdb.connect(":memory:")
	DuckDBTable("Stock Ledger Entry").sync(conn)
	conn.register("captured", table)
	conn.execute('INSERT INTO "tabStock Ledger Entry" BY NAME SELECT * FROM captured')
	conn.unregister("captured")
	live_sql = frappe.db.sql

	def sql(query, *args, **kwargs):
		if "tabStock Ledger Entry" in str(query):
			raise AssertionError(f"Live ledger query during a snapshot run: {query}")
		return live_sql(query, *args, **kwargs)

	with (
		patch(
			LATEST_SYNC, return_value=frappe._dict(filename="snapshot", creation=synced_at or now_datetime())
		),
		patch(f"{SNAPSHOT}.get_duckdb", return_value=DuckDBConnection(conn)),
		patch.object(frappe.db, "sql", side_effect=sql),
	):
		yield


def execute_from_snapshot(filters):
	with ledger_snapshot(capture_ledger(filters)):
		return stock_balance.execute_snapshot_report(deepcopy(filters))


class TestStockBalanceSnapshot(ERPNextTestSuite):
	def setUp(self):
		self.item = make_item("_Test DuckDB Stock Item").name
		self.filters = frappe._dict(
			company="_Test Company",
			item_code=[self.item],
			warehouse=["Stores - _TC"],
			from_date=add_days(today(), -5),
			to_date=today(),
		)

	def assert_snapshot_matches(self, **filters):
		filters = frappe._dict(self.filters, **filters)
		self.assertEqual(execute_from_snapshot(filters), stock_balance.execute(deepcopy(filters)))

	def make_movement(self, **kwargs):
		args = dict(
			item_code=self.item, to_warehouse="Stores - _TC", posting_date=today(), posting_time="12:00:00"
		)
		return make_stock_entry(**{**args, **kwargs})

	def issue(self, qty, **kwargs):
		return self.make_movement(qty=qty, from_warehouse="Stores - _TC", to_warehouse=None, **kwargs)

	def set_ledger_values(self, voucher_no, values):
		frappe.db.set_value("Stock Ledger Entry", {"voucher_no": voucher_no}, values)

	def close_stock(self, from_date, to_date):
		with patch("erpnext.stock.doctype.stock_closing_entry.stock_closing_entry.enqueue"):
			closing = frappe.get_doc(
				doctype="Stock Closing Entry",
				company=self.filters.company,
				from_date=from_date,
				to_date=to_date,
			).submit()
		closing.create_stock_closing_balance_entries()
		closing.db_set("status", "Completed")

	def use_item(self, name, properties):
		self.item = make_item(name, properties).name
		self.filters.item_code = [self.item]

	def test_empty_result_keeps_columns(self):
		self.assert_snapshot_matches()

	def test_opening_receipts_and_issues(self):
		self.make_movement(qty=10, basic_rate=100, posting_date=add_days(today(), -10))
		self.make_movement(qty=5, basic_rate=150)
		self.issue(3)
		self.assert_snapshot_matches()

	def test_ordinary_movements_are_summed_in_duckdb(self):
		self.make_movement(qty=10, basic_rate=100, posting_date=add_days(today(), -10))
		self.make_movement(qty=5, basic_rate=150)
		expected = stock_balance.execute(deepcopy(self.filters))
		with patch.object(stock_balance.StockBalanceReport, "prepare_item_warehouse_map") as replay:
			self.assertEqual(execute_from_snapshot(self.filters), expected)
			replay.assert_not_called()

	def test_stock_reconciliation_resets_the_balance(self):
		self.make_movement(qty=10, basic_rate=100, posting_date=add_days(today(), -10))
		create_stock_reconciliation(
			item_code=self.item,
			warehouse="Stores - _TC",
			qty=7,
			rate=120,
			posting_date=add_days(today(), -2),
			posting_time="12:00:00",
		)
		self.make_movement(qty=2, basic_rate=130, posting_date=add_days(today(), -1))
		self.assert_snapshot_matches()

	def test_adjustment_entry_is_a_plain_delta(self):
		self.make_movement(qty=10, basic_rate=100, posting_date=add_days(today(), -10))
		reconciliation = create_stock_reconciliation(
			item_code=self.item, warehouse="Stores - _TC", qty=7, rate=120, posting_date=add_days(today(), -2)
		)
		self.set_ledger_values(
			reconciliation.name, {"is_adjustment_entry": 1, "actual_qty": 0, "stock_value_difference": -50}
		)
		self.assert_snapshot_matches()

	def test_small_negative_amounts_keep_the_live_rounding(self):
		self.make_movement(qty=10, basic_rate=100)
		entry = self.issue(1)
		self.set_ledger_values(entry.name, {"actual_qty": -0.00001, "stock_value_difference": -0.00001})
		self.assert_snapshot_matches()

	def test_amounts_are_summed_as_floats(self):
		receipt = self.make_movement(qty=1, basic_rate=100)
		issue = self.issue(1)
		for entry, amount in ((receipt, 471636.5443), (issue, -459509.9528)):
			self.set_ledger_values(entry.name, {"actual_qty": amount, "stock_value_difference": amount})
		self.assert_snapshot_matches()

	def test_cancelled_entries_are_ignored(self):
		self.make_movement(qty=10, basic_rate=100)
		self.make_movement(qty=2, basic_rate=100).cancel()
		self.assert_snapshot_matches()

	def test_item_and_warehouse_filters(self):
		self.make_movement(qty=10, basic_rate=100)
		parent = frappe.db.get_value("Warehouse", "Stores - _TC", "parent_warehouse")
		warehouse_type = frappe.get_doc(doctype="Warehouse Type", name="_Test DuckDB Stores").insert().name
		frappe.db.set_value("Warehouse", "Stores - _TC", "warehouse_type", warehouse_type)
		self.assert_snapshot_matches(warehouse=[parent], item_group="Products")
		self.assert_snapshot_matches(warehouse=None, warehouse_type=warehouse_type)
		self.assert_snapshot_matches(brand="No matching brand")

	def test_stock_closing_balance_is_the_opening(self):
		self.make_movement(qty=10, basic_rate=100, posting_date=add_days(today(), -10))
		self.close_stock(add_days(today(), -10), add_days(today(), -6))
		self.make_movement(qty=5, basic_rate=100)
		self.assert_snapshot_matches()

	def test_closing_after_the_sync_is_not_used(self):
		self.make_movement(qty=10, basic_rate=100, posting_date=add_days(today(), -10))
		ledger, synced_at = capture_ledger(self.filters), now_datetime()
		expected = stock_balance.execute(deepcopy(self.filters))
		self.make_movement(qty=5, basic_rate=100, posting_date=add_days(today(), -8))
		self.close_stock(add_days(today(), -10), add_days(today(), -6))
		with ledger_snapshot(ledger, synced_at):
			self.assertEqual(stock_balance.execute_snapshot_report(deepcopy(self.filters)), expected)

	def test_opening_voucher_cancelled_after_the_sync_stays_opening(self):
		reconciliation = create_stock_reconciliation(
			item_code=self.item,
			warehouse="Stores - _TC",
			qty=10,
			rate=100,
			purpose="Opening Stock",
			expense_account=frappe.db.get_value(
				"Account", {"account_type": "Temporary", "company": self.filters.company}
			),
			posting_date=add_days(today(), -2),
		)
		ledger, expected = capture_ledger(self.filters), stock_balance.execute(deepcopy(self.filters))
		reconciliation.cancel()
		with ledger_snapshot(ledger):
			self.assertEqual(stock_balance.execute_snapshot_report(deepcopy(self.filters)), expected)

	def test_inventory_dimension_filter_and_grouping(self):
		for entry in (
			self.make_movement(qty=10, basic_rate=100, posting_date=add_days(today(), -10)),
			self.make_movement(qty=5, basic_rate=100),
		):
			self.set_ledger_values(entry.name, {"project": "DuckDB Project"})
		dimensions = [frappe._dict(fieldname="project", doctype="Project")]
		with patch.object(stock_balance, "get_inventory_dimensions", return_value=dimensions):
			self.assert_snapshot_matches(project=["DuckDB Project"], show_dimension_wise_stock=1)

	def test_sparse_inventory_dimensions_group_like_the_live_key(self):
		values = (("A", ""), ("", "A"), ("B", "A"), (None, None), ("", ""))
		for index, (project, detail) in enumerate(values):
			entry = self.make_movement(
				qty=index + 1, basic_rate=100, posting_date=add_days(today(), index - 4)
			)
			self.set_ledger_values(entry.name, {"project": project, "voucher_detail_no": detail})
		dimensions = [
			frappe._dict(fieldname=field, doctype="Project") for field in ("project", "voucher_detail_no")
		]
		with patch.object(stock_balance, "get_inventory_dimensions", return_value=dimensions):
			for dimension_filters in ({"show_dimension_wise_stock": 1}, {"project": ["A", "B"]}, {}):
				with self.subTest(filters=dimension_filters):
					self.assert_snapshot_matches(**dimension_filters)

	def test_serial_and_batch_items(self):
		self.use_item("_Test DuckDB Serial Item", {"has_serial_no": 1, "serial_no_series": "DUCK-SN-.#####"})
		self.make_movement(qty=3, basic_rate=100)
		self.assert_snapshot_matches()
		self.use_item(
			"_Test DuckDB Batch Item",
			{"has_batch_no": 1, "create_new_batch": 1, "batch_number_series": "DUCK-.#####"},
		)
		receipt = self.make_movement(qty=10, basic_rate=100, posting_date=add_days(today(), -10))
		batch = frappe.db.get_value(
			"Serial and Batch Entry", {"parent": receipt.items[0].serial_and_batch_bundle}, "batch_no"
		)
		self.issue(3, batch_no=batch)
		self.assert_snapshot_matches()

	def test_changes_after_the_sync_are_not_read(self):
		self.make_movement(qty=10, basic_rate=100)
		ledger = capture_ledger(self.filters)
		expected = stock_balance.execute(deepcopy(self.filters))
		self.make_movement(qty=5, basic_rate=100)
		with ledger_snapshot(ledger):
			self.assertEqual(stock_balance.execute_snapshot_report(deepcopy(self.filters)), expected)
		self.assertNotEqual(stock_balance.execute(deepcopy(self.filters)), expected)

	def test_ageing_columns_are_refused(self):
		filters = frappe._dict(self.filters, show_stock_ageing_data=1)
		with patch(LATEST_SYNC, side_effect=AssertionError("Sync opened")):
			self.assertRaises(frappe.ValidationError, stock_balance.execute_snapshot_report, filters)

	def test_requires_a_sync(self):
		with patch(LATEST_SYNC, return_value=None):
			self.assertRaises(
				frappe.ValidationError, stock_balance.execute_snapshot_report, deepcopy(self.filters)
			)


@patch.object(live_tests, "execute", execute_from_snapshot)
class TestStockBalanceFromSnapshot(live_tests.TestStockBalance):
	"""The live Stock Balance tests, with the report read from a snapshot of the ledger. A snapshot
	refuses ageing columns, which test_ageing_columns_are_refused covers."""

	test_show_stock_ageing_data_adds_ageing_columns = None
