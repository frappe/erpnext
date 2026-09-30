# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.item_price_stock.item_price_stock import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestItemPriceStock(ERPNextTestSuite):
	def run_report(self, **extra):
		return execute(frappe._dict(extra))[1]

	def test_price_and_stock_shown(self):
		item = "_Test Item"

		frappe.get_doc(
			{
				"doctype": "Item Price",
				"item_code": item,
				"price_list": "Standard Selling",
				"price_list_rate": 300,
			}
		).insert()

		make_stock_entry(
			item_code=item,
			to_warehouse="Stores - _TC",
			qty=7,
			rate=100,
			posting_date="2026-06-01",
		)

		rows = self.run_report(item_code=item)
		warehouse_rows = [
			row
			for row in rows
			if row["warehouse"] == "Stores - _TC" and row["selling_price_list"] == "Standard Selling"
		]

		self.assertEqual(len(warehouse_rows), 1)
		row = warehouse_rows[0]
		self.assertEqual(row["item_code"], item)
		self.assertEqual(row["selling_price_list"], "Standard Selling")
		self.assertEqual(row["selling_rate"], 300)
		self.assertEqual(row["stock_available"], 7)
