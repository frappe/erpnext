# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import json
import os

import frappe

from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.tests.utils import ERPNextTestSuite


class TestItemsToBeRequested(ERPNextTestSuite):
	def listed_items(self):
		path = os.path.join(os.path.dirname(__file__), "items_to_be_requested.json")
		query = json.load(open(path))["query"]
		return [row[0] for row in frappe.db.sql(query)]

	def test_disabled_items_are_not_listed(self):
		item = make_item(properties={"is_stock_item": 1}).name
		make_sales_order(item_code=item, qty=3, warehouse="Stores - _TC")
		self.assertIn(item, self.listed_items())

		frappe.db.set_value("Item", item, "disabled", 1)

		self.assertNotIn(item, self.listed_items())
