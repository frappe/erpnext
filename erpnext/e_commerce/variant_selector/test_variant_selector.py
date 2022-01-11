import unittest

import frappe

from erpnext.controllers.item_variant import create_variant
from erpnext.e_commerce.doctype.website_item.website_item import make_website_item
from erpnext.stock.doctype.item.test_item import make_item

test_dependencies = ["Item"]

class TestVariantSelector(unittest.TestCase):

	def setUp(self) -> None:
		self.template_item = make_item("Test-Tshirt-Temp", {
			"has_variant": 1,
			"variant_based_on": "Item Attribute",
			"attributes": [
				{
					"attribute": "Test Size"
				},
				{
					"attribute": "Test Colour"
				}
			]
		})

		# create L-R, L-G, M-R, M-G and S-R
		for size in ("Large", "Medium",):
			for colour in ("Red", "Green",):
				variant = create_variant("Test-Tshirt-Temp", {
					"Test Size": size,
					"Test Colour": colour
				})
				variant.save()

		variant = create_variant("Test-Tshirt-Temp", {
			"Test Size": "Small",
			"Test Colour": "Red"
		})
		variant.save()

	def tearDown(self):
		frappe.db.rollback()

	def test_item_attributes(self):
		"""
			Test if the right attributes are fetched in the popup.
			(Attributes must only come from active items)

			Attribute selection must not be linked to Website Items.
		"""
		from erpnext.e_commerce.variant_selector.utils import get_attributes_and_values

		make_website_item(self.template_item) # publish template not variants

		attr_data = get_attributes_and_values("Test-Tshirt-Temp")

		self.assertEqual(attr_data[0]["attribute"], "Test Size")
		self.assertEqual(attr_data[1]["attribute"], "Test Colour")
		self.assertEqual(len(attr_data[0]["values"]), 3) # ['Small', 'Medium', 'Large']
		self.assertEqual(len(attr_data[1]["values"]), 2) # ['Red', 'Green']

		# disable small red tshirt, now there are no small tshirts.
		# but there are some red tshirts
		small_variant = frappe.get_doc("Item", "Test-Tshirt-Temp-S-R")
		small_variant.disabled = 1
		small_variant.save() # trigger cache rebuild

		attr_data = get_attributes_and_values("Test-Tshirt-Temp")

		# Only L and M attribute values must be fetched since S is disabled
		self.assertEqual(len(attr_data[0]["values"]), 2)  # ['Medium', 'Large']

		# teardown
		small_variant.disabled = 1
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
		from erpnext.e_commerce.variant_selector.utils import get_next_attribute_and_values

		next_values = get_next_attribute_and_values("Test-Tshirt-Temp", selected_attributes={"Test Size": "Small"})
		next_colours = next_values["valid_options_for_attributes"]["Test Colour"]
		filtered_items = next_values["filtered_items"]

		self.assertEqual(len(next_colours), 1)
		self.assertEqual(next_colours.pop(), "Red")
		self.assertEqual(len(filtered_items), 1)
		self.assertEqual(filtered_items.pop(), "Test-Tshirt-Temp-S-R")
