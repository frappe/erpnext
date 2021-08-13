# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

test_dependencies = ["Item"]

class TestProductDataEngine(unittest.TestCase):
	"Test Products Querying for Product Listing."
	def test_product_list_ordering(self):
		"Check if website items appear by ranking."
		pass

	def test_product_list_paging(self):
		pass

	def test_product_list_with_field_filter(self):
		pass

	def test_product_list_with_attribute_filter(self):
		pass

	def test_product_list_with_discount_filter(self):
		pass

	def test_product_list_with_mixed_filtes(self):
		pass

	def test_product_list_with_mixed_filtes_item_group(self):
		pass

	def test_products_in_multiple_item_groups(self):
		"Check if product is visible on multiple item group pages barring its own."
		pass

	def test_product_list_with_variants(self):
		pass

