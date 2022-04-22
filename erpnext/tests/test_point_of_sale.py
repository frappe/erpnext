# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import unittest

import frappe

from erpnext.accounts.doctype.pos_profile.test_pos_profile import make_pos_profile
from erpnext.selling.page.point_of_sale.point_of_sale import get_items
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry


class TestPointOfSale(unittest.TestCase):
	@classmethod
	def setUpClass(cls) -> None:
		frappe.db.savepoint("before_test_point_of_sale")

	@classmethod
	def tearDownClass(cls) -> None:
		frappe.db.rollback(save_point="before_test_point_of_sale")

	def test_item_search(self):
		"""
		Test Stock and Service Item Search.
		"""

		pos_profile = make_pos_profile(name="Test POS Profile for Search")
		item1 = make_item("Test Search Stock Item", {"is_stock_item": 1})
		make_stock_entry(
			item_code="Test Search Stock Item",
			qty=10,
			to_warehouse="_Test Warehouse - _TC",
			rate=500,
		)

		result = get_items(
			start=0,
			page_length=20,
			price_list=None,
			item_group=item1.item_group,
			pos_profile=pos_profile.name,
			search_term="Test Search Stock Item",
		)
		filtered_items = result.get("items")

		self.assertEqual(len(filtered_items), 1)
		self.assertEqual(filtered_items[0]["item_code"], item1.item_code)
		self.assertEqual(filtered_items[0]["actual_qty"], 10)

		item2 = make_item("Test Search Service Item", {"is_stock_item": 0})
		result = get_items(
			start=0,
			page_length=20,
			price_list=None,
			item_group=item2.item_group,
			pos_profile=pos_profile.name,
			search_term="Test Search Service Item",
		)
		filtered_items = result.get("items")

		self.assertEqual(len(filtered_items), 1)
		self.assertEqual(filtered_items[0]["item_code"], item2.item_code)
