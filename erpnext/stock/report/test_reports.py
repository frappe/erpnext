import unittest

import frappe
from frappe.core.doctype.report.report import get_report_module_dotted_path

MODULE = "Stock"

DEFAULT_FILTERS = {
	"company": "_Test Company",
	"from_date": "2010-01-01",
	"to_date": "2030-01-01",
}

REPORT_FILTER_MAP = {
	"Stock Ledger": {"_optional": True},
	"Stock Balance": {"_optional": True},
	"Stock Projected Qty": {"_optional": True},
	"Batch-Wise Balance History": {},
	"Itemwise Recommended Reorder Level": {"item_group": "All Item Groups"},
	"COGS By Item Group": {},
	"Stock Qty vs Serial No Count": {"warehouse": "_Test Warehouse - _TC"},
	"Stock and Account Value Comparison": {
		"company": "_Test Company with perpetual inventory",
		"account": "Stock In Hand - TCP1",
		"as_on_date": "2021-01-01",
	},
	"Product Bundle Balance": {"date": "2022-01-01", "_optional": True},
	"Stock Analytics": {
		"from_date": "2021-01-01",
		"to_date": "2021-12-31",
		"value_quantity": "Quantity",
		"_optional": True,
	},
	"Warehouse wise Item Balance Age and Value": {"_optional": True},
	"Item Variant Details": {"item": "_Test Variant Item",},
	"Total Stock Summary": {"group_by": "warehouse",},
	"Batch Item Expiry Status": {},
	"Stock Ageing": {"range1": 30, "range2": 60, "range3": 90, "_optional": True},
}

# When _opional is set to True, these filters are added one at a time to default filters in test.
OPTIONAL_FILTERS = {
	"warehouse": "_Test Warehouse - _TC",
	"item": "_Test Item",
	"item_group": "_Test Item Group",
}


class TestReports(unittest.TestCase):
	def test_execute_all_stock_reports(self):
		for report, filter in REPORT_FILTER_MAP.items():
			filter = frappe._dict(DEFAULT_FILTERS.copy()).update(filter)
			report_execute_fn = get_report_module_dotted_path(MODULE, report) + ".execute"
			frappe.get_attr(report_execute_fn)(filter)

			# try each optional filter
			if filter.get("_optional"):
				for key, value in OPTIONAL_FILTERS.items():
					frappe.get_attr(report_execute_fn)(filter.copy().update({key: value}))
