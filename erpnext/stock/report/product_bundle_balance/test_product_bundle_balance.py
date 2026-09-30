# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.product_bundle_balance.product_bundle_balance import execute
from erpnext.tests.utils import ERPNextTestSuite

WH = "Stores - _TC"


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
