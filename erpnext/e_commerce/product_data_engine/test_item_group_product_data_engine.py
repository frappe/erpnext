# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import unittest

import frappe

from erpnext.e_commerce.api import get_product_filter_data
from erpnext.e_commerce.doctype.website_item.test_website_item import create_regular_web_item

test_dependencies = ["Item", "Item Group"]


class TestItemGroupProductDataEngine(unittest.TestCase):
	"Test Products & Sub-Category Querying for Product Listing on Item Group Page."

	def setUp(self):
		item_codes = [
			("Test Mobile A", "_Test Item Group B"),
			("Test Mobile B", "_Test Item Group B"),
			("Test Mobile C", "_Test Item Group B - 1"),
			("Test Mobile D", "_Test Item Group B - 1"),
			("Test Mobile E", "_Test Item Group B - 2"),
		]
		for item in item_codes:
			item_code = item[0]
			item_args = {"item_group": item[1]}
			if not frappe.db.exists("Website Item", {"item_code": item_code}):
				create_regular_web_item(item_code, item_args=item_args)

		frappe.db.set_value("Item Group", "_Test Item Group B - 1", "show_in_website", 1)
		frappe.db.set_value("Item Group", "_Test Item Group B - 2", "show_in_website", 1)

	def tearDown(self):
		frappe.db.rollback()

	def test_product_listing_in_item_group(self):
		"Test if only products belonging to the Item Group are fetched."
		result = get_product_filter_data(
			query_args={
				"field_filters": {},
				"attribute_filters": {},
				"start": 0,
				"item_group": "_Test Item Group B",
			}
		)

		items = result.get("items")
		item_codes = [item.get("item_code") for item in items]

		self.assertEqual(len(items), 2)
		self.assertIn("Test Mobile A", item_codes)
		self.assertNotIn("Test Mobile C", item_codes)

	def test_products_in_multiple_item_groups(self):
		"""Test if product is visible on multiple item group pages barring its own."""
		website_item = frappe.get_doc("Website Item", {"item_code": "Test Mobile E"})

		# show item belonging to '_Test Item Group B - 2' in '_Test Item Group B - 1' as well
		website_item.append("website_item_groups", {"item_group": "_Test Item Group B - 1"})
		website_item.save()

		result = get_product_filter_data(
			query_args={
				"field_filters": {},
				"attribute_filters": {},
				"start": 0,
				"item_group": "_Test Item Group B - 1",
			}
		)

		items = result.get("items")
		item_codes = [item.get("item_code") for item in items]

		self.assertEqual(len(items), 3)
		self.assertIn("Test Mobile E", item_codes)  # visible in other item groups
		self.assertIn("Test Mobile C", item_codes)
		self.assertIn("Test Mobile D", item_codes)

		result = get_product_filter_data(
			query_args={
				"field_filters": {},
				"attribute_filters": {},
				"start": 0,
				"item_group": "_Test Item Group B - 2",
			}
		)

		items = result.get("items")

		self.assertEqual(len(items), 1)
		self.assertEqual(items[0].get("item_code"), "Test Mobile E")  # visible in own item group

	def test_item_group_with_sub_groups(self):
		"Test Valid Sub Item Groups in Item Group Page."
		frappe.db.set_value("Item Group", "_Test Item Group B - 2", "show_in_website", 0)

		result = get_product_filter_data(
			query_args={
				"field_filters": {},
				"attribute_filters": {},
				"start": 0,
				"item_group": "_Test Item Group B",
			}
		)

		self.assertTrue(bool(result.get("sub_categories")))

		child_groups = [d.name for d in result.get("sub_categories")]
		# check if child group is fetched if shown in website
		self.assertIn("_Test Item Group B - 1", child_groups)

		frappe.db.set_value("Item Group", "_Test Item Group B - 2", "show_in_website", 1)
		result = get_product_filter_data(
			query_args={
				"field_filters": {},
				"attribute_filters": {},
				"start": 0,
				"item_group": "_Test Item Group B",
			}
		)
		child_groups = [d.name for d in result.get("sub_categories")]

		# check if child group is fetched if shown in website
		self.assertIn("_Test Item Group B - 1", child_groups)
		self.assertIn("_Test Item Group B - 2", child_groups)

	def test_item_group_page_with_descendants_included(self):
		"""
		Test if 'include_descendants' pulls Items belonging to descendant Item Groups (Level 2 & 3).
		> _Test Item Group B [Level 1]
		        > _Test Item Group B - 1 [Level 2]
		                > _Test Item Group B - 1 - 1 [Level 3]
		"""
		frappe.get_doc(
			{  # create Level 3 nested child group
				"doctype": "Item Group",
				"is_group": 1,
				"item_group_name": "_Test Item Group B - 1 - 1",
				"parent_item_group": "_Test Item Group B - 1",
			}
		).insert()

		create_regular_web_item(  # create an item belonging to level 3 item group
			"Test Mobile F", item_args={"item_group": "_Test Item Group B - 1 - 1"}
		)

		frappe.db.set_value("Item Group", "_Test Item Group B - 1 - 1", "show_in_website", 1)

		# enable 'include descendants' in Level 1
		frappe.db.set_value("Item Group", "_Test Item Group B", "include_descendants", 1)

		result = get_product_filter_data(
			query_args={
				"field_filters": {},
				"attribute_filters": {},
				"start": 0,
				"item_group": "_Test Item Group B",
			}
		)

		items = result.get("items")
		item_codes = [item.get("item_code") for item in items]

		# check if all sub groups' items are pulled
		self.assertEqual(len(items), 6)
		self.assertIn("Test Mobile A", item_codes)
		self.assertIn("Test Mobile C", item_codes)
		self.assertIn("Test Mobile E", item_codes)
		self.assertIn("Test Mobile F", item_codes)
