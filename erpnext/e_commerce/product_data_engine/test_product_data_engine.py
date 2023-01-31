# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import unittest

import frappe

from erpnext.e_commerce.doctype.e_commerce_settings.test_e_commerce_settings import (
	setup_e_commerce_settings,
)
from erpnext.e_commerce.doctype.website_item.test_website_item import create_regular_web_item
from erpnext.e_commerce.product_data_engine.filters import ProductFiltersBuilder
from erpnext.e_commerce.product_data_engine.query import ProductQuery

test_dependencies = ["Item", "Item Group"]


class TestProductDataEngine(unittest.TestCase):
	"Test Products Querying and Filters for Product Listing."

	@classmethod
	def setUpClass(cls):
		item_codes = [
			("Test 11I Laptop", "Products"),  # rank 1
			("Test 12I Laptop", "Products"),  # rank 2
			("Test 13I Laptop", "Products"),  # rank 3
			("Test 14I Laptop", "Raw Material"),  # rank 4
			("Test 15I Laptop", "Raw Material"),  # rank 5
			("Test 16I Laptop", "Raw Material"),  # rank 6
			("Test 17I Laptop", "Products"),  # rank 7
		]
		for index, item in enumerate(item_codes, start=1):
			item_code = item[0]
			item_args = {"item_group": item[1]}
			web_args = {"ranking": index}
			if not frappe.db.exists("Website Item", {"item_code": item_code}):
				create_regular_web_item(item_code, item_args=item_args, web_args=web_args)

		setup_e_commerce_settings(
			{
				"products_per_page": 4,
				"enable_field_filters": 1,
				"filter_fields": [{"fieldname": "item_group"}],
				"enable_attribute_filters": 1,
				"filter_attributes": [{"attribute": "Test Size"}],
				"company": "_Test Company",
				"enabled": 1,
				"default_customer_group": "_Test Customer Group",
				"price_list": "_Test Price List India",
			}
		)
		frappe.local.shopping_cart_settings = None

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()

	def test_product_list_ordering_and_paging(self):
		"Test if website items appear by ranking on different pages."
		engine = ProductQuery()
		result = engine.query(attributes={}, fields={}, search_term=None, start=0, item_group=None)
		items = result.get("items")

		self.assertIsNotNone(items)
		self.assertEqual(len(items), 4)
		self.assertGreater(result.get("items_count"), 4)

		# check if items appear as per ranking set in setUpClass
		self.assertEqual(items[0].get("item_code"), "Test 17I Laptop")
		self.assertEqual(items[1].get("item_code"), "Test 16I Laptop")
		self.assertEqual(items[2].get("item_code"), "Test 15I Laptop")
		self.assertEqual(items[3].get("item_code"), "Test 14I Laptop")

		# check next page
		result = engine.query(attributes={}, fields={}, search_term=None, start=4, item_group=None)
		items = result.get("items")

		# check if items appear as per ranking set in setUpClass on next page
		self.assertEqual(items[0].get("item_code"), "Test 13I Laptop")
		self.assertEqual(items[1].get("item_code"), "Test 12I Laptop")
		self.assertEqual(items[2].get("item_code"), "Test 11I Laptop")

	def test_change_product_ranking(self):
		"Test if item on second page appear on first if ranking is changed."
		item_code = "Test 12I Laptop"
		old_ranking = frappe.db.get_value("Website Item", {"item_code": item_code}, "ranking")

		# low rank, appears on second page
		self.assertEqual(old_ranking, 2)

		# set ranking as highest rank
		frappe.db.set_value("Website Item", {"item_code": item_code}, "ranking", 10)

		engine = ProductQuery()
		result = engine.query(attributes={}, fields={}, search_term=None, start=0, item_group=None)
		items = result.get("items")

		# check if item is the first item on the first page
		self.assertEqual(items[0].get("item_code"), item_code)
		self.assertEqual(items[1].get("item_code"), "Test 17I Laptop")

		# tear down
		frappe.db.set_value("Website Item", {"item_code": item_code}, "ranking", old_ranking)

	def test_product_list_field_filter_builder(self):
		"Test if field filters are fetched correctly."
		frappe.db.set_value("Item Group", "Raw Material", "show_in_website", 0)

		filter_engine = ProductFiltersBuilder()
		field_filters = filter_engine.get_field_filters()

		# Web Items belonging to 'Products' and 'Raw Material' are available
		# but only 'Products' has 'show_in_website' enabled
		item_group_filters = field_filters[0]
		docfield = item_group_filters[0]
		valid_item_groups = item_group_filters[1]

		self.assertEqual(docfield.options, "Item Group")
		self.assertIn("Products", valid_item_groups)
		self.assertNotIn("Raw Material", valid_item_groups)

		frappe.db.set_value("Item Group", "Raw Material", "show_in_website", 1)
		field_filters = filter_engine.get_field_filters()

		#'Products' and 'Raw Materials' both have 'show_in_website' enabled
		item_group_filters = field_filters[0]
		docfield = item_group_filters[0]
		valid_item_groups = item_group_filters[1]

		self.assertEqual(docfield.options, "Item Group")
		self.assertIn("Products", valid_item_groups)
		self.assertIn("Raw Material", valid_item_groups)

	def test_product_list_with_field_filter(self):
		"Test if field filters are applied correctly."
		field_filters = {"item_group": "Raw Material"}

		engine = ProductQuery()
		result = engine.query(
			attributes={}, fields=field_filters, search_term=None, start=0, item_group=None
		)
		items = result.get("items")

		# check if only 'Raw Material' are fetched in the right order
		self.assertEqual(len(items), 3)
		self.assertEqual(items[0].get("item_code"), "Test 16I Laptop")
		self.assertEqual(items[1].get("item_code"), "Test 15I Laptop")

	# def test_product_list_with_field_filter_table_multiselect(self):
	# 	TODO
	# 	pass

	def test_product_list_attribute_filter_builder(self):
		"Test if attribute filters are fetched correctly."
		create_variant_web_item()

		filter_engine = ProductFiltersBuilder()
		attribute_filter = filter_engine.get_attribute_filters()[0]
		attribute_values = attribute_filter.item_attribute_values

		self.assertEqual(attribute_filter.name, "Test Size")
		self.assertGreater(len(attribute_values), 0)
		self.assertIn("Large", attribute_values)

	def test_product_list_with_attribute_filter(self):
		"Test if attribute filters are applied correctly."
		create_variant_web_item()

		attribute_filters = {"Test Size": ["Large"]}
		engine = ProductQuery()
		result = engine.query(
			attributes=attribute_filters, fields={}, search_term=None, start=0, item_group=None
		)
		items = result.get("items")

		# check if only items with Test Size 'Large' are fetched
		self.assertEqual(len(items), 1)
		self.assertEqual(items[0].get("item_code"), "Test Web Item-L")

	def test_product_list_discount_filter_builder(self):
		"Test if discount filters are fetched correctly."
		from erpnext.e_commerce.doctype.website_item.test_website_item import (
			make_web_item_price,
			make_web_pricing_rule,
		)

		item_code = "Test 12I Laptop"
		make_web_item_price(item_code=item_code)
		make_web_pricing_rule(title=f"Test Pricing Rule for {item_code}", item_code=item_code, selling=1)

		setup_e_commerce_settings({"show_price": 1})
		frappe.local.shopping_cart_settings = None

		engine = ProductQuery()
		result = engine.query(attributes={}, fields={}, search_term=None, start=4, item_group=None)
		self.assertTrue(bool(result.get("discounts")))

		filter_engine = ProductFiltersBuilder()
		discount_filters = filter_engine.get_discount_filters(result["discounts"])

		self.assertEqual(len(discount_filters[0]), 2)
		self.assertEqual(discount_filters[0][0], 10)
		self.assertEqual(discount_filters[0][1], "10% and below")

	def test_product_list_with_discount_filters(self):
		"Test if discount filters are applied correctly."
		from erpnext.e_commerce.doctype.website_item.test_website_item import (
			make_web_item_price,
			make_web_pricing_rule,
		)

		field_filters = {"discount": [10]}

		make_web_item_price(item_code="Test 12I Laptop")
		make_web_pricing_rule(
			title="Test Pricing Rule for Test 12I Laptop",  # 10% discount
			item_code="Test 12I Laptop",
			selling=1,
		)
		make_web_item_price(item_code="Test 13I Laptop")
		make_web_pricing_rule(
			title="Test Pricing Rule for Test 13I Laptop",  # 15% discount
			item_code="Test 13I Laptop",
			discount_percentage=15,
			selling=1,
		)

		setup_e_commerce_settings({"show_price": 1})
		frappe.local.shopping_cart_settings = None

		engine = ProductQuery()
		result = engine.query(
			attributes={}, fields=field_filters, search_term=None, start=0, item_group=None
		)
		items = result.get("items")

		# check if only product with 10% and below discount are fetched
		self.assertEqual(len(items), 1)
		self.assertEqual(items[0].get("item_code"), "Test 12I Laptop")

	def test_product_list_with_api(self):
		"Test products listing using API."
		from erpnext.e_commerce.api import get_product_filter_data

		create_variant_web_item()

		result = get_product_filter_data(
			query_args={
				"field_filters": {"item_group": "Products"},
				"attribute_filters": {"Test Size": ["Large"]},
				"start": 0,
			}
		)

		items = result.get("items")

		self.assertEqual(len(items), 1)
		self.assertEqual(items[0].get("item_code"), "Test Web Item-L")

	def test_product_list_with_variants(self):
		"Test if variants are hideen on hiding variants in settings."
		create_variant_web_item()

		setup_e_commerce_settings({"enable_attribute_filters": 0, "hide_variants": 1})
		frappe.local.shopping_cart_settings = None

		attribute_filters = {"Test Size": ["Large"]}
		engine = ProductQuery()
		result = engine.query(
			attributes=attribute_filters, fields={}, search_term=None, start=0, item_group=None
		)
		items = result.get("items")

		# check if any variants are fetched even though published variant exists
		self.assertEqual(len(items), 0)

		# tear down
		setup_e_commerce_settings({"enable_attribute_filters": 1, "hide_variants": 0})

	def test_custom_field_as_filter(self):
		"Test if custom field functions as filter correctly."
		from frappe.custom.doctype.custom_field.custom_field import create_custom_field

		create_custom_field(
			"Website Item",
			dict(
				owner="Administrator",
				fieldname="supplier",
				label="Supplier",
				fieldtype="Link",
				options="Supplier",
				insert_after="on_backorder",
			),
		)

		frappe.db.set_value(
			"Website Item", {"item_code": "Test 11I Laptop"}, "supplier", "_Test Supplier"
		)
		frappe.db.set_value(
			"Website Item", {"item_code": "Test 12I Laptop"}, "supplier", "_Test Supplier 1"
		)

		settings = frappe.get_doc("E Commerce Settings")
		settings.append("filter_fields", {"fieldname": "supplier"})
		settings.save()

		filter_engine = ProductFiltersBuilder()
		field_filters = filter_engine.get_field_filters()
		custom_filter = field_filters[1]
		filter_values = custom_filter[1]

		self.assertEqual(custom_filter[0].options, "Supplier")
		self.assertEqual(len(filter_values), 2)
		self.assertIn("_Test Supplier", filter_values)

		# test if custom filter works in query
		field_filters = {"supplier": "_Test Supplier 1"}
		engine = ProductQuery()
		result = engine.query(
			attributes={}, fields=field_filters, search_term=None, start=0, item_group=None
		)
		items = result.get("items")

		# check if only 'Raw Material' are fetched in the right order
		self.assertEqual(len(items), 1)
		self.assertEqual(items[0].get("item_code"), "Test 12I Laptop")


def create_variant_web_item():
	"Create Variant and Template Website Items."
	from erpnext.controllers.item_variant import create_variant
	from erpnext.e_commerce.doctype.website_item.website_item import make_website_item
	from erpnext.stock.doctype.item.test_item import make_item

	make_item(
		"Test Web Item",
		{
			"has_variant": 1,
			"variant_based_on": "Item Attribute",
			"attributes": [{"attribute": "Test Size"}],
		},
	)
	if not frappe.db.exists("Item", "Test Web Item-L"):
		variant = create_variant("Test Web Item", {"Test Size": "Large"})
		variant.save()

	if not frappe.db.exists("Website Item", {"variant_of": "Test Web Item"}):
		make_website_item(variant, save=True)
