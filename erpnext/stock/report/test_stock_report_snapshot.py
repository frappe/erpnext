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
from frappe.core.doctype.duckdb_sync.duckdb_sync import DuckDBSync
from frappe.database.duckdb.schema import DuckDBTable
from frappe.query_builder.builder import MariaDB, Postgres
from frappe.query_builder.functions import Cast
from frappe.utils import add_days, today

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import create_stock_reconciliation
from erpnext.stock.report.stock_ageing import stock_ageing
from erpnext.stock.report.stock_balance import stock_balance
from erpnext.stock.report.stock_ledger import stock_ledger
from erpnext.stock.report.stock_report_snapshot import StockReportSnapshot
from erpnext.tests.utils import ERPNextTestSuite


class TestStockReportSnapshot(ERPNextTestSuite):
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

	def test_reports_match_with_opening_receipts_and_issues(self):
		self.make_movement(qty=10, basic_rate=100, posting_date=add_days(today(), -10))
		self.make_movement(qty=5, basic_rate=150)
		self.make_movement(qty=3, from_warehouse="Stores - _TC", to_warehouse=None)
		for report in (stock_ledger, stock_balance, stock_ageing):
			with self.subTest(report=report.__name__):
				self.assert_snapshot_matches(report)
		self.assert_snapshot_matches(stock_balance, show_stock_ageing_data=1)
		self.assert_snapshot_matches(stock_ageing, show_warehouse_wise_stock=1)

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

	def test_ageing_calculates_remaining_layers_before_python(self):
		self.make_movement(qty=10, basic_rate=100, posting_date=add_days(today(), -2))
		self.make_movement(qty=5, basic_rate=200, posting_date=add_days(today(), -1))
		self.make_movement(qty=12, from_warehouse="Stores - _TC", to_warehouse=None)
		expected = stock_ageing.execute(deepcopy(self.filters))
		with patch.object(
			stock_ageing.FIFOSlots,
			"_process_stock_ledger_entry",
			side_effect=AssertionError("Unexpected ledger replay"),
		):
			self.assertEqual(expected, self.run_snapshot(stock_ageing, self.capture_ledger()))

	def test_unfiltered_valuation_prefetch_uses_report_ledger_scope(self):
		company = frappe.get_doc(
			doctype="Company",
			company_name="_Test Valuation Prefetch Company",
			abbr="VPF",
			country="India",
			default_currency="INR",
			default_warehouse="",
		).insert()
		brand = frappe.get_doc(doctype="Brand", brand="_Test Valuation Prefetch Brand").insert().name
		warehouse_type = (
			frappe.get_doc(doctype="Warehouse Type", name="_Test Valuation Prefetch").insert().name
		)
		warehouse = "Stores - VPF"
		frappe.db.set_value("Warehouse", warehouse, "warehouse_type", warehouse_type)
		items = {}
		for case in (
			"relevant",
			"default_one",
			"default_two",
			"no_ledger",
			"future",
			"cancelled",
			"other_company",
			"other_warehouse",
			"other_brand",
		):
			self.set_item(
				f"_Test Valuation Prefetch {case}",
				{"valuation_method": "" if case.startswith("default") else "FIFO", "brand": brand},
			)
			items[case] = self.item
			if case == "no_ledger":
				continue
			entry = self.make_movement(
				qty=1,
				basic_rate=100,
				company="_Test Company" if case == "other_company" else company.name,
				to_warehouse="Stores - _TC"
				if case == "other_company"
				else ("Work In Progress - VPF" if case == "other_warehouse" else warehouse),
				posting_date=today() if case == "future" else add_days(today(), -2),
			)
			if case == "cancelled":
				entry.cancel()
			if case == "other_brand":
				frappe.db.set_value("Item", self.item, "brand", None)
		filters = frappe._dict(
			company=company.name, to_date=add_days(today(), -1), warehouse=[warehouse], item_code=None
		)
		expected = {
			items["relevant"]: "FIFO",
			items["default_one"]: "Moving Average",
			items["default_two"]: "Moving Average",
			items["other_brand"]: "FIFO",
		}
		cases = [
			(filters, expected),
			(
				frappe._dict(filters, brand=brand),
				{key: value for key, value in expected.items() if key != items["other_brand"]},
			),
			(frappe._dict(filters, warehouse=None, warehouse_type=warehouse_type), expected),
			(frappe._dict(filters, brand="No matching prefetch brand"), {}),
		]
		for report_filters, methods in cases:
			self.assert_prefetched_valuation_methods(report_filters, methods)
		table = self.capture_ledger(list(items.values()))
		self.item = items["no_ledger"]
		self.make_movement(
			qty=1,
			basic_rate=100,
			company=company.name,
			to_warehouse=warehouse,
			posting_date=add_days(today(), -2),
		)
		for report_filters, methods in cases:
			with patch.object(StockReportSnapshot, "get_connection", return_value=self.connect(table)):
				with StockReportSnapshot("Stock Ageing", report_filters) as snapshot:
					self.assert_prefetched_valuation_methods(report_filters, methods, snapshot)

	def assert_prefetched_valuation_methods(self, filters, expected, snapshot=None):
		with patch("erpnext.stock.utils.get_valuation_method", return_value="Moving Average") as default:
			slots = stock_ageing.FIFOSlots(filters, snapshot=snapshot)
			slots._prefetch_valuation_methods()
			self.assertEqual(slots.valuation_method_by_item, expected)
			self.assertEqual(default.call_count, int("Moving Average" in expected.values()))

	def test_stock_closing_balance_matches(self):
		self.make_movement(qty=10, basic_rate=100, posting_date=add_days(today(), -10))
		with patch("erpnext.stock.doctype.stock_closing_entry.stock_closing_entry.enqueue"):
			closing = frappe.get_doc(
				doctype="Stock Closing Entry",
				company=self.filters.company,
				from_date=add_days(today(), -10),
				to_date=add_days(today(), -6),
			).submit()
		closing.create_stock_closing_balance_entries()
		closing.db_set("status", "Completed")
		self.make_movement(qty=5, basic_rate=100)
		self.assert_snapshot_matches(stock_balance)
		self.assert_snapshot_matches(stock_balance, show_stock_ageing_data=1)

	def test_small_negative_amounts_use_existing_rounding(self):
		self.make_movement(qty=10, basic_rate=100)
		entry = self.make_movement(qty=1, from_warehouse="Stores - _TC", to_warehouse=None)
		frappe.db.set_value(
			"Stock Ledger Entry",
			{"voucher_no": entry.name},
			{"actual_qty": -0.00001, "stock_value_difference": -0.00001},
		)
		self.assert_snapshot_matches(stock_balance)

	def test_empty_snapshot_preserves_columns(self):
		for report in self.reports:
			with self.subTest(report=report.__name__):
				self.assert_snapshot_matches(report)

	def test_stock_balance_aggregates_before_python(self):
		self.make_movement(qty=10, basic_rate=100, posting_date=add_days(today(), -10))
		self.make_movement(qty=5, basic_rate=150)
		expected = stock_balance.execute(deepcopy(self.filters))
		with patch.object(stock_balance.StockBalanceReport, "prepare_item_warehouse_map") as process_entry:
			self.assertEqual(expected, self.run_snapshot(stock_balance, self.capture_ledger()))
			process_entry.assert_not_called()

	def test_batch_opening_and_bundle_details_match(self):
		self.set_item(
			"_Test DuckDB Batch Item",
			{"has_batch_no": 1, "create_new_batch": 1, "batch_number_series": "DUCK-.#####"},
		)
		receipt = self.make_movement(qty=10, basic_rate=100, posting_date=add_days(today(), -10))
		batch = frappe.get_value(
			"Serial and Batch Entry", {"parent": receipt.items[0].serial_and_batch_bundle}, "batch_no"
		)
		self.make_movement(qty=3, batch_no=batch, from_warehouse="Stores - _TC", to_warehouse=None)
		self.assert_snapshot_matches(stock_ledger, batch_no=batch, segregate_serial_batch_bundle=1)
		self.assert_snapshot_matches(stock_balance, show_stock_ageing_data=1)
		self.assert_snapshot_matches(stock_ageing)

	def test_serial_bundle_details_match(self):
		self.set_item("_Test DuckDB Serial Item", {"has_serial_no": 1, "serial_no_series": "DUCK-SN-.#####"})
		self.make_movement(qty=3, basic_rate=100)
		self.assert_snapshot_matches(stock_ledger, segregate_serial_batch_bundle=1)
		self.assert_snapshot_matches(stock_balance, show_stock_ageing_data=1)
		self.assert_snapshot_matches(stock_ageing)

	def test_inventory_dimension_opening_and_grouping_match(self):
		opening = self.make_movement(qty=10, basic_rate=100, posting_date=add_days(today(), -10))
		current = self.make_movement(qty=5, basic_rate=100)
		for entry in (opening, current):
			frappe.db.set_value("Stock Ledger Entry", {"voucher_no": entry.name}, "project", "DuckDB Project")
		dimensions = [frappe._dict(fieldname="project", doctype="Project")]
		with (
			patch.object(stock_ledger, "get_inventory_dimensions", return_value=dimensions),
			patch.object(stock_balance, "get_inventory_dimensions", return_value=dimensions),
		):
			self.assert_snapshot_matches(stock_ledger, project=["DuckDB Project"])
			self.assert_snapshot_matches(
				stock_balance, project=["DuckDB Project"], show_dimension_wise_stock=1
			)

	def test_filters_and_cancelled_entries_match(self):
		self.make_movement(qty=10, basic_rate=100)
		cancelled = self.make_movement(qty=2, basic_rate=100)
		cancelled.cancel()
		for report in self.reports:
			with self.subTest(report=report.__name__):
				self.assert_snapshot_matches(report)
		parent = frappe.get_value("Warehouse", "Stores - _TC", "parent_warehouse")
		self.assert_snapshot_matches(stock_balance, warehouse=[parent], item_group="Products")
		self.assert_snapshot_matches(stock_ledger, warehouse=[parent])
		self.assert_snapshot_matches(stock_ageing, warehouse=[parent])
		self.assert_snapshot_matches(stock_balance, brand="No matching brand")

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
		return stock_ledger, stock_balance, stock_ageing
