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

	def test_price_list_shows_current_prices_with_uom_and_party(self):
		from frappe.utils import add_days, today

		item = make_item(
			properties={
				"is_stock_item": 1,
				"stock_uom": "Nos",
				"uoms": [{"uom": "Box", "conversion_factor": 12}],
			}
		).name
		for rate, extra in (
			(500, {}),
			(450, {"customer": "_Test Customer"}),
			(400, {"valid_from": add_days(today(), -60), "valid_upto": add_days(today(), -31)}),
			(6000, {"uom": "Box"}),
		):
			frappe.get_doc(
				{
					"doctype": "Item Price",
					"item_code": item,
					"price_list": "Standard Selling",
					"price_list_rate": rate,
					**extra,
				}
			).insert()

		columns, data = self.run_report()
		prices = sorted(self.cell(columns, self.row_for(columns, data, item), "Sales Price List").split(", "))

		self.assertEqual(
			[price.split(" ", 1)[1] for price in prices],
			[
				"450.0 - Standard Selling / Nos (_Test Customer)",
				"500.0 - Standard Selling / Nos",
				"6000.0 - Standard Selling / Box",
			],
		)
