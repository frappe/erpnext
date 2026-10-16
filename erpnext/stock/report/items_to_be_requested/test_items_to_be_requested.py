# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.report.items_to_be_requested.items_to_be_requested import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestItemsToBeRequested(ERPNextTestSuite):
	def test_disabled_items_are_not_listed(self):
		item = make_item(properties={"is_stock_item": 1}).name
		make_sales_order(item_code=item, qty=3, warehouse="Stores - _TC")
		frappe.db.set_value("Item", item, "disabled", 1)

		data = execute(frappe._dict())[1]

		self.assertNotIn(item, [row.get("item_code") for row in data])
