# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from copy import deepcopy
from unittest.mock import patch

import frappe
from frappe.utils import add_days, today

from erpnext.stock.report.stock_balance import stock_balance
from erpnext.stock.report.stock_snapshot_test_utils import StockSnapshotReportMixin, StockSnapshotTestCase


class TestStockBalanceSnapshotReport(StockSnapshotReportMixin, StockSnapshotTestCase):
	report = stock_balance
	receipt_options = ({}, {"show_stock_ageing_data": 1})

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

	def test_stock_balance_aggregates_before_python(self):
		self.make_movement(qty=10, basic_rate=100, posting_date=add_days(today(), -10))
		self.make_movement(qty=5, basic_rate=150)
		expected = stock_balance.execute(deepcopy(self.filters))
		with patch.object(stock_balance.StockBalanceReport, "prepare_item_warehouse_map") as process_entry:
			self.assertEqual(expected, self.run_snapshot(stock_balance, self.capture_ledger()))
			process_entry.assert_not_called()

	def test_balance_aggregates_sparse_inventory_dimensions(self):
		for index, (project, detail) in enumerate((("A", ""), ("", "A"), ("B", "A"), (None, None), ("", ""))):
			entry = self.make_movement(
				qty=index + 1, basic_rate=100, posting_date=add_days(today(), index - 4)
			)
			frappe.db.set_value(
				"Stock Ledger Entry",
				{"voucher_no": entry.name},
				{"project": project, "voucher_detail_no": detail},
			)
		dimensions = [
			frappe._dict(fieldname=field, doctype="Project") for field in ("project", "voucher_detail_no")
		]
		with patch.object(stock_balance, "get_inventory_dimensions", return_value=dimensions):
			for dimension_filters in ({"show_dimension_wise_stock": 1}, {"project": ["A", "B"]}, {}):
				filters = frappe._dict(self.filters, **dimension_filters)
				expected = stock_balance.execute(deepcopy(filters))
				with patch.object(
					stock_balance.StockBalanceReport,
					"prepare_item_warehouse_map",
					side_effect=AssertionError("Unexpected ledger replay"),
				):
					self.assertEqual(
						expected, self.run_snapshot(stock_balance, self.capture_ledger(), filters)
					)

	def test_serial_bundle_details_match(self):
		self.set_item("_Test DuckDB Serial Item", {"has_serial_no": 1, "serial_no_series": "DUCK-SN-.#####"})
		self.make_movement(qty=3, basic_rate=100)
		self.assert_snapshot_matches(stock_balance, show_stock_ageing_data=1)

	def test_batch_opening_and_bundle_details_match(self):
		self.make_batch_history()
		self.assert_snapshot_matches(stock_balance, show_stock_ageing_data=1)

	def test_inventory_dimension_opening_and_grouping_match(self):
		opening = self.make_movement(qty=10, basic_rate=100, posting_date=add_days(today(), -10))
		current = self.make_movement(qty=5, basic_rate=100)
		for entry in (opening, current):
			frappe.db.set_value("Stock Ledger Entry", {"voucher_no": entry.name}, "project", "DuckDB Project")
		dimensions = [frappe._dict(fieldname="project", doctype="Project")]
		with patch.object(stock_balance, "get_inventory_dimensions", return_value=dimensions):
			self.assert_snapshot_matches(
				stock_balance, project=["DuckDB Project"], show_dimension_wise_stock=1
			)

	def test_item_group_and_brand_filters(self):
		self.make_movement(qty=10, basic_rate=100)
		parent = frappe.get_value("Warehouse", "Stores - _TC", "parent_warehouse")
		self.assert_snapshot_matches(stock_balance, warehouse=[parent], item_group="Products")
		self.assert_snapshot_matches(stock_balance, brand="No matching brand")
