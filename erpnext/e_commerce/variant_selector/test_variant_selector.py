import unittest

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.controllers.item_variant import create_variant
from erpnext.e_commerce.doctype.e_commerce_settings.test_e_commerce_settings import (
	setup_e_commerce_settings,
)
from erpnext.e_commerce.doctype.website_item.website_item import make_website_item
from erpnext.e_commerce.variant_selector.utils import get_next_attribute_and_values
from erpnext.stock.doctype.item.test_item import make_item

test_dependencies = ["Item"]


class TestVariantSelector(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		template_item = make_item(
			"Test-Tshirt-Temp",
			{
				"has_variant": 1,
				"variant_based_on": "Item Attribute",
				"attributes": [{"attribute": "Test Size"}, {"attribute": "Test Colour"}],
			},
		)

		# create L-R, L-G, M-R, M-G and S-R
		for size in (
			"Large",
			"Medium",
		):
			for colour in (
				"Red",
				"Green",
			):
				variant = create_variant("Test-Tshirt-Temp", {"Test Size": size, "Test Colour": colour})
				variant.save()

		variant = create_variant("Test-Tshirt-Temp", {"Test Size": "Small", "Test Colour": "Red"})
		variant.save()

		make_website_item(template_item)  # publish template not variants

	def test_item_attributes(self):
		"""
		Test if the right attributes are fetched in the popup.
		(Attributes must only come from active items)

		Attribute selection must not be linked to Website Items.
		"""
		from erpnext.e_commerce.variant_selector.utils import get_attributes_and_values

		attr_data = get_attributes_and_values("Test-Tshirt-Temp")

		self.assertEqual(attr_data[0]["attribute"], "Test Size")
		self.assertEqual(attr_data[1]["attribute"], "Test Colour")
		self.assertEqual(len(attr_data[0]["values"]), 3)  # ['Small', 'Medium', 'Large']
		self.assertEqual(len(attr_data[1]["values"]), 2)  # ['Red', 'Green']

		# disable small red tshirt, now there are no small tshirts.
		# but there are some red tshirts
		small_variant = frappe.get_doc("Item", "Test-Tshirt-Temp-S-R")
		small_variant.disabled = 1
		small_variant.save()  # trigger cache rebuild

		attr_data = get_attributes_and_values("Test-Tshirt-Temp")

		# Only L and M attribute values must be fetched since S is disabled
		self.assertEqual(len(attr_data[0]["values"]), 2)  # ['Medium', 'Large']

		# teardown
		small_variant.disabled = 0
		small_variant.save()

	def test_next_item_variant_values(self):
		"""
		Test if on selecting an attribute value, the next possible values
		are filtered accordingly.
		Values that dont apply should not be fetched.
		E.g.
		There is a ** Small-Red ** Tshirt. No other colour in this size.
		On selecting ** Small **, only ** Red ** should be selectable next.
		"""
		next_values = get_next_attribute_and_values(
			"Test-Tshirt-Temp", selected_attributes={"Test Size": "Small"}
		)
		next_colours = next_values["valid_options_for_attributes"]["Test Colour"]
		filtered_items = next_values["filtered_items"]

		self.assertEqual(len(next_colours), 1)
		self.assertEqual(next_colours.pop(), "Red")
		self.assertEqual(len(filtered_items), 1)
		self.assertEqual(filtered_items.pop(), "Test-Tshirt-Temp-S-R")

	def test_exact_match_with_price(self):
		"""
		Test price fetching and matching of variant without Website Item
		"""
		from erpnext.e_commerce.doctype.website_item.test_website_item import make_web_item_price

		frappe.set_user("Administrator")
		setup_e_commerce_settings(
			{
				"company": "_Test Company",
				"enabled": 1,
				"default_customer_group": "_Test Customer Group",
				"price_list": "_Test Price List India",
				"show_price": 1,
			}
		)

		make_web_item_price(item_code="Test-Tshirt-Temp-S-R", price_list_rate=100)

		frappe.local.shopping_cart_settings = None  # clear cached settings values
		next_values = get_next_attribute_and_values(
			"Test-Tshirt-Temp", selected_attributes={"Test Size": "Small", "Test Colour": "Red"}
		)
		print(">>>>", next_values)
		price_info = next_values["product_info"]["price"]

		self.assertEqual(next_values["exact_match"][0], "Test-Tshirt-Temp-S-R")
		self.assertEqual(next_values["exact_match"][0], "Test-Tshirt-Temp-S-R")
		self.assertEqual(price_info["price_list_rate"], 100.0)
		self.assertEqual(price_info["formatted_price_sales_uom"], "₹ 100.00")
