# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from datetime import datetime
from decimal import Decimal

import duckdb
import frappe
import pyarrow as pa
from frappe.query_builder import Order
from frappe.query_builder.functions import IfNull, Sum
from pypika.analytics import RowNumber

from erpnext.stock.report.stock_ledger.stock_ledger_snapshot import get_opening_query
from erpnext.stock.report.stock_report_snapshot import StockReportSnapshot
from erpnext.tests.utils import ERPNextTestSuite


class TestStockLedgerSnapshot(ERPNextTestSuite):
	def test_latest_balances_match_window_ordering_and_null_values(self):
		for null_order in (
			"NULLS_FIRST",
			"NULLS_LAST",
			"NULLS_FIRST_ON_ASC_LAST_ON_DESC",
			"NULLS_LAST_ON_ASC_FIRST_ON_DESC",
		):
			with self.subTest(null_order=null_order):
				self.compare_opening_queries(self.make_table(), null_order)

	def test_empty_history_preserves_zero_totals(self):
		self.assertEqual(self.compare_opening_queries(self.make_table().slice(0, 0)), [(0.0, 0.0)])

	def test_filters_apply_before_latest_balance_selection(self):
		ledger = frappe.qb.DocType("Stock Ledger Entry")
		condition = (
			(ledger.item_code == "A") & (ledger.warehouse == "W1") & (ledger.creation <= datetime(2026, 1, 1))
		)
		self.assertEqual(self.compare_opening_queries(self.make_table(), condition=condition), [(1.0, 100.0)])

	def compare_opening_queries(self, table, null_order="NULLS_LAST", condition=None):
		ledger = frappe.qb.DocType("Stock Ledger Entry")
		source = frappe.qb.from_(ledger)
		if condition is not None:
			source = source.where(condition)
		window = source.select(
			ledger.qty_after_transaction,
			ledger.stock_value,
			RowNumber()
			.over(ledger.item_code, ledger.warehouse)
			.orderby(ledger.posting_datetime, ledger.creation, ledger.name, order=Order.desc)
			.as_("rn"),
		)
		reference = (
			frappe.qb.from_(window)
			.select(IfNull(Sum(window.qty_after_transaction), 0.0), IfNull(Sum(window.stock_value), 0.0))
			.where(window.rn == 1)
		)
		with duckdb.connect(":memory:", config={"default_null_order": null_order}) as conn:
			conn.from_arrow(table).create("tabStock Ledger Entry")
			snapshot = StockReportSnapshot.__new__(StockReportSnapshot)
			snapshot.conn, snapshot.tables, snapshot.filters = conn, {}, {}
			expected = snapshot.run(reference)
			actual = snapshot.run(get_opening_query(source, ledger, snapshot))
			self.assertEqual(actual, expected)
			return actual

	def make_table(self):
		rows = [
			("A", "W1", 1, 1, "first", 1, 100),
			("A", "W1", 1, 2, "B", 2, None),
			("A", "W1", 1, 2, "C", 3, 300),
			("A", "W1", 1, None, "D", 4, 400),
			("A", "W1", None, 3, "E", 5, 500),
			("A", "W2", 2, 3, "F", 7, 700),
			("B", "W1", 3, 3, "G", None, 800),
			("B", "W1", 3, 3, "H'quoted", 9, None),
		]
		schema = pa.schema(
			[
				("item_code", pa.string()),
				("warehouse", pa.string()),
				("posting_datetime", pa.timestamp("us")),
				("creation", pa.timestamp("us")),
				("name", pa.string()),
				("qty_after_transaction", pa.decimal128(21, 9)),
				("stock_value", pa.decimal128(21, 9)),
			]
		)
		values = []
		for item, warehouse, posting, creation, name, qty, value in rows:
			values.append(
				dict(
					zip(
						schema.names,
						(
							item,
							warehouse,
							datetime(2026, 1, posting) if posting else None,
							datetime(2026, 1, creation) if creation else None,
							name,
							Decimal(qty) if qty is not None else None,
							Decimal(value) if value is not None else None,
						),
						strict=True,
					)
				)
			)
		return pa.Table.from_pylist(values, schema=schema)
