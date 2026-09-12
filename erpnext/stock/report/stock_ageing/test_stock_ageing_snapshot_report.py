# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from copy import deepcopy
from unittest.mock import patch

import frappe
from frappe.utils import add_days, today

from erpnext.stock.report.stock_ageing import stock_ageing
from erpnext.stock.report.stock_report_snapshot import StockReportSnapshot
from erpnext.stock.report.stock_snapshot_test_utils import StockSnapshotReportMixin, StockSnapshotTestCase


class TestStockAgeingSnapshotReport(StockSnapshotReportMixin, StockSnapshotTestCase):
	report = stock_ageing
	receipt_options = ({}, {"show_warehouse_wise_stock": 1})

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

	def test_serial_bundle_details_match(self):
		self.set_item("_Test DuckDB Serial Item", {"has_serial_no": 1, "serial_no_series": "DUCK-SN-.#####"})
		self.make_movement(qty=3, basic_rate=100)
		self.assert_snapshot_matches(stock_ageing)

	def test_batch_opening_and_bundle_details_match(self):
		self.make_batch_history()
		self.assert_snapshot_matches(stock_ageing)
