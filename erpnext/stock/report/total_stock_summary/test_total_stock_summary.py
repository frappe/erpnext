# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.total_stock_summary.total_stock_summary import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestTotalStockSummary(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = frappe._dict({"company": "_Test Company", "group_by": "Warehouse", **extra})
		return execute(filters)[1]

	def test_warehouse_wise_quantity(self):
		item = "_Test Item"
		warehouse = "Stores - _TC"  # clean zero baseline for _Test Item
		make_stock_entry(item_code=item, to_warehouse=warehouse, qty=10, rate=100)

		# rows are (warehouse, item_code, description, actual_qty)
		row = next(r for r in self.run_report() if r[0] == warehouse and r[1] == item)
		self.assertEqual(row[3], 10)

	def test_only_non_zero_bins_are_listed(self):
		item = "_Test Item 2"
		warehouse = "Stores - _TC"  # clean zero baseline for _Test Item 2
		# receive then issue everything -> bin actual_qty back to zero
		make_stock_entry(item_code=item, to_warehouse=warehouse, qty=5, rate=100)
		make_stock_entry(item_code=item, from_warehouse=warehouse, qty=5)

		self.assertFalse([r for r in self.run_report() if r[0] == warehouse and r[1] == item])
