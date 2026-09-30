# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.item_prices.item_prices import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestItemPrices(ERPNextTestSuite):
	"""Correctness tests for the Item Prices report."""

	def run_report(self, **extra):
		filters = frappe._dict({"items": "Enabled Items only", **extra})
		return execute(filters)[:2]

	# The report returns string-format columns ("Label:fieldtype:width"); resolve positions
	# by label so the tests self-correct if the column order changes.
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

	def test_item_selling_price_listed(self):
		"""A Standard Selling Item Price shows up in the Sales Price List column."""
		item = "_Test Item"
		frappe.get_doc(
			{
				"doctype": "Item Price",
				"item_code": item,
				"price_list": "Standard Selling",
				"price_list_rate": 250,
			}
		).insert()

		columns, data = self.run_report()
		row = self.row_for(columns, data, item)
		self.assertIn("250.0", self.cell(columns, row, "Sales Price List"))
		self.assertIn("Standard Selling", self.cell(columns, row, "Sales Price List"))
		# A selling price must not leak into the buying column.
		self.assertNotIn("250.0", self.cell(columns, row, "Purchase Price List") or "")
		self.assertNotIn("Standard Selling", self.cell(columns, row, "Purchase Price List") or "")

	def test_item_buying_price_listed(self):
		"""A Standard Buying Item Price shows up in the Purchase Price List column."""
		item = "_Test Item 2"
		frappe.get_doc(
			{
				"doctype": "Item Price",
				"item_code": item,
				"price_list": "Standard Buying",
				"price_list_rate": 175,
			}
		).insert()

		columns, data = self.run_report()
		row = self.row_for(columns, data, item)
		self.assertIn("175.0", self.cell(columns, row, "Purchase Price List"))
		self.assertIn("Standard Buying", self.cell(columns, row, "Purchase Price List"))
		# A buying price must not leak into the selling column.
		self.assertNotIn("175.0", self.cell(columns, row, "Sales Price List") or "")
		self.assertNotIn("Standard Buying", self.cell(columns, row, "Sales Price List") or "")

	def test_last_purchase_rate_from_receipt(self):
		"""The latest purchase rate (from a Purchase Receipt) shows in the Last Purchase Rate column."""
		# a fresh item has no other committed purchase records, so it is the only (and latest) row
		item = make_item(properties={"is_stock_item": 1, "is_purchase_item": 1}).name
		make_purchase_receipt(
			item_code=item, qty=5, rate=500, company="_Test Company", posting_date="2026-06-01"
		)

		columns, data = self.run_report()
		row = self.row_for(columns, data, item)
		self.assertEqual(self.cell(columns, row, "Last Purchase Rate"), 500)

	def test_valuation_rate_from_stock(self):
		"""The Bin valuation rate shows in the Valuation Rate column."""
		# a fresh item has no other committed bins, so its average valuation is exactly this receipt's rate
		item = make_item(properties={"is_stock_item": 1}).name
		make_stock_entry(
			item_code=item, to_warehouse="Stores - _TC", qty=10, rate=250, posting_date="2026-06-01"
		)

		columns, data = self.run_report()
		row = self.row_for(columns, data, item)
		self.assertEqual(self.cell(columns, row, "Valuation Rate"), 250)
