# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.warehouse_wise_item_balance_age_and_value.warehouse_wise_item_balance_age_and_value import (
	execute,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestWarehouseWiseItemBalanceAgeAndValue(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"from_date": "2026-01-01",
				"to_date": "2026-12-31",
				"warehouse": "Stores - _TC",
			}
		)
		filters.update(extra)
		return execute(filters)[1]

	def test_balance_qty_and_value(self):
		item_code = "_Test Item"
		warehouse = "Stores - _TC"

		make_stock_entry(
			item_code=item_code,
			to_warehouse=warehouse,
			qty=10,
			rate=100,
			posting_date="2026-06-01",
		)
		make_stock_entry(
			item_code=item_code,
			from_warehouse=warehouse,
			qty=4,
			posting_date="2026-06-02",
		)

		data = self.run_report(item_code=item_code)

		# With a single (leaf) warehouse filter the row shape is:
		# [item, item_name, item_group, brand, value, age, bal_qty]
		rows = [row for row in data if row[0] == item_code]
		self.assertEqual(len(rows), 1)

		row = rows[0]
		# index 6 -> balance qty in the filtered warehouse
		self.assertEqual(row[6], 6)
		# index 4 -> total stock value (6 units @ 100)
		self.assertEqual(row[4], 600)
