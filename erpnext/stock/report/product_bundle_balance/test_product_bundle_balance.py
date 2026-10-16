# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.product_bundle_balance.product_bundle_balance import execute
from erpnext.tests.utils import ERPNextTestSuite

WH = "Stores - _TC"


class TestProductBundleBalanceQuantity(UnitTestCase):
	def test_bundle_qty_with_non_positive_component_stock(self):
		parent = "Office Stationery Kit"
		child_a = "Notebook"
		child_b = "Pen"
		items = (
			{parent: frappe._dict(item_name=parent)},
			{parent: [frappe._dict(item_code=child_a, qty=2), frappe._dict(item_code=child_b, qty=1)]},
			[parent],
			[child_a, child_b],
		)
		for actual_qty, expected_qty in ((-5, 0), (0, 0), (5, 2)):
			with self.subTest(actual_qty=actual_qty):
				stock_balance = {
					child_a: {WH: frappe._dict(qty_after_transaction=actual_qty, company="_Test Company")},
					child_b: {WH: frappe._dict(qty_after_transaction=10, company="_Test Company")},
				}
				with (
					patch(
						"erpnext.stock.report.product_bundle_balance.product_bundle_balance.get_items",
						return_value=items,
					),
					patch(
						"erpnext.stock.report.product_bundle_balance.product_bundle_balance.get_stock_balance",
						return_value=stock_balance,
					),
				):
					data = execute()[1]

				self.assertEqual(len(data), 3)
				self.assertEqual(data[0]["bundle_qty"], expected_qty)
				self.assertEqual(data[1]["bundle_qty"], expected_qty)
				self.assertEqual(data[1]["actual_qty"], actual_qty)
				self.assertEqual(data[2]["bundle_qty"], 10)


class TestProductBundleBalance(ERPNextTestSuite):
	def make_bundle(self, parent, child_qty):
		bundle = frappe.get_doc({"doctype": "Product Bundle", "new_item_code": parent})
		for item_code, qty in child_qty.items():
			bundle.append("items", {"item_code": item_code, "qty": qty})
		bundle.insert()
		bundle.submit()

	def run_report(self, item_code):
		filters = frappe._dict({"company": "_Test Company", "item_code": item_code})
		return execute(filters)[1]

	def test_bundle_qty_is_limited_by_scarcest_child(self):
		# Reuse the bootstrap stock items as children. They start at zero in `Stores - _TC`,
		# so transacting there gives a clean, deterministic balance for this warehouse's row.
		parent = make_item(properties={"is_stock_item": 0, "is_sales_item": 1}).name
		child_a = "_Test Item"
		child_b = "_Test Item 2"
		self.make_bundle(parent, {child_a: 2, child_b: 1})

		make_stock_entry(item_code=child_a, to_warehouse=WH, qty=10, rate=100)
		make_stock_entry(item_code=child_b, to_warehouse=WH, qty=3, rate=100)

		data = self.run_report(parent)
		parent_row = next(
			r for r in data if r["item_code"] == parent and r["indent"] == 0 and r["warehouse"] == WH
		)
		# min(10 // 2, 3 // 1) = min(5, 3) = 3 buildable bundles
		self.assertEqual(parent_row["bundle_qty"], 3)

		row_a = next(
			r for r in data if r["item_code"] == child_a and r["indent"] == 1 and r["warehouse"] == WH
		)
		row_b = next(
			r for r in data if r["item_code"] == child_b and r["indent"] == 1 and r["warehouse"] == WH
		)
		self.assertEqual((row_a["actual_qty"], row_a["minimum_qty"], row_a["bundle_qty"]), (10, 2, 5))
		self.assertEqual((row_b["actual_qty"], row_b["minimum_qty"], row_b["bundle_qty"]), (3, 1, 3))

	def test_balance_is_taken_on_the_report_date(self):
		from frappe.utils import add_days, today

		parent = make_item(properties={"is_stock_item": 0}).name
		child = make_item(properties={"is_stock_item": 1}).name
		self.make_bundle(parent, {child: 2})
		make_stock_entry(
			item_code=child, target=WH, qty=10, basic_rate=100, posting_date=add_days(today(), -10)
		)
		make_stock_entry(item_code=child, target=WH, qty=10, basic_rate=100)

		filters = frappe._dict(
			{"company": "_Test Company", "item_code": parent, "date": add_days(today(), -5)}
		)
		data = execute(filters)[1]

		self.assertEqual(
			[(row["actual_qty"], row["bundle_qty"]) for row in data if row.get("indent")], [(10, 5)]
		)
