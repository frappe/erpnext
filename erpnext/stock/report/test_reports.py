import unittest
from typing import List, Tuple

import frappe

from erpnext.tests.utils import ReportFilters, ReportName, execute_script_report

DEFAULT_FILTERS = {
	"company": "_Test Company",
	"from_date": "2010-01-01",
	"to_date": "2030-01-01",
}


batch = frappe.db.get_value("Batch", fieldname=["name"], as_dict=True, order_by="creation desc")

REPORT_FILTER_TEST_CASES: List[Tuple[ReportName, ReportFilters]] = [
	("Stock Ledger", {"_optional": True}),
	("Stock Ledger", {"batch_no": batch}),
	("Stock Ledger", {"item_code": "_Test Item", "warehouse": "_Test Warehouse - _TC"}),
	("Stock Balance", {"_optional": True}),
	("Stock Projected Qty", {"_optional": True}),
	("Batch-Wise Balance History", {}),
	("Itemwise Recommended Reorder Level", {"item_group": "All Item Groups"}),
	("COGS By Item Group", {}),
	("Stock Qty vs Serial No Count", {"warehouse": "_Test Warehouse - _TC"}),
	(
		"Stock and Account Value Comparison",
		{
			"company": "_Test Company with perpetual inventory",
			"account": "Stock In Hand - TCP1",
			"as_on_date": "2021-01-01",
		},
	),
	("Product Bundle Balance", {"date": "2022-01-01", "_optional": True}),
	(
		"Stock Analytics",
		{
			"from_date": "2021-01-01",
			"to_date": "2021-12-31",
			"value_quantity": "Quantity",
			"_optional": True,
		},
	),
	("Warehouse wise Item Balance Age and Value", {"_optional": True}),
	(
		"Item Variant Details",
		{
			"item": "_Test Variant Item",
		},
	),
	(
		"Total Stock Summary",
		{
			"group_by": "warehouse",
		},
	),
	("Batch Item Expiry Status", {}),
	("Incorrect Stock Value Report", {"company": "_Test Company with perpetual inventory"}),
	("Incorrect Serial No Valuation", {}),
	("Incorrect Balance Qty After Transaction", {}),
	("Supplier-Wise Sales Analytics", {}),
	("Item Prices", {"items": "Enabled Items only"}),
	("Delayed Item Report", {"based_on": "Sales Invoice"}),
	("Delayed Item Report", {"based_on": "Delivery Note"}),
	("Stock Ageing", {"range1": 30, "range2": 60, "range3": 90, "_optional": True}),
	("Stock Ledger Invariant Check", {"warehouse": "_Test Warehouse - _TC", "item": "_Test Item"}),
]

OPTIONAL_FILTERS = {
	"warehouse": "_Test Warehouse - _TC",
	"item": "_Test Item",
	"item_group": "_Test Item Group",
}


class TestReports(unittest.TestCase):
	def test_execute_all_stock_reports(self):
		"""Test that all script report in stock modules are executable with supported filters"""
		for report, filter in REPORT_FILTER_TEST_CASES:
			with self.subTest(report=report):
				execute_script_report(
					report_name=report,
					module="Stock",
					filters=filter,
					default_filters=DEFAULT_FILTERS,
					optional_filters=OPTIONAL_FILTERS if filter.get("_optional") else None,
				)
