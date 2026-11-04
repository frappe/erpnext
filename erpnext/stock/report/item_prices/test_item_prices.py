# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.report.item_prices.item_prices import execute


class TestItemPrices(FrappeTestCase):
	def run_report(self, **extra):
		filters = frappe._dict({"items": "Enabled Items only", **extra})
		return execute(filters)[:2]

	@staticmethod
	def labels(columns):
		return [c.split(":")[0] if isinstance(c, str) else c.get("label") for c in columns]

	def row_for(self, columns, data, item_code):
		item_idx = self.labels(columns).index("Item")
		for row in data:
			if row[item_idx] == item_code:
				return row
		self.fail(f"No report row found for item {item_code}")
		return None

	def cell(self, columns, row, label):
		return row[self.labels(columns).index(label)]

	def test_last_purchase_rate_is_per_stock_uom(self):
		item = make_item(
			properties={
				"is_stock_item": 1,
				"stock_uom": "Nos",
				"uoms": [{"uom": "Box", "conversion_factor": 12}],
			}
		).name
		make_purchase_receipt(
			item_code=item, qty=2, rate=1200, uom="Box", stock_uom="Nos", conversion_factor=12
		)

		columns, data = self.run_report()

		self.assertEqual(self.cell(columns, self.row_for(columns, data, item), "Last Purchase Rate"), 100)

	def test_later_purchase_on_the_same_day_sets_the_last_purchase_rate(self):
		item = make_item(properties={"is_stock_item": 1}).name
		for rate in (350, 300, 325):
			make_purchase_receipt(item_code=item, qty=1, rate=rate, posting_date="2026-06-01")

		columns, data = self.run_report()

		self.assertEqual(self.cell(columns, self.row_for(columns, data, item), "Last Purchase Rate"), 325)
