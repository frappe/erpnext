# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt


import frappe

from erpnext.stock.doctype.item_attribute.item_attribute import ItemAttributeIncrementError
from erpnext.tests.utils import ERPNextTestSuite


class TestItemAttribute(ERPNextTestSuite):
	def setUp(self):
		super().setUp()
		if frappe.db.exists("Item Attribute", "_Test_Length"):
			frappe.delete_doc("Item Attribute", "_Test_Length")

	def test_numeric_item_attribute(self):
		item_attribute = frappe.get_doc(
			{
				"doctype": "Item Attribute",
				"attribute_name": "_Test_Length",
				"numeric_values": 1,
				"from_range": 0.0,
				"to_range": 100.0,
				"increment": 0,
			}
		)

		self.assertRaises(ItemAttributeIncrementError, item_attribute.save)

		item_attribute.increment = 0.5
		item_attribute.save()

	def test_validate_existing_items_finds_variants(self):
		# validate_exising_items() joins Item Variant Attribute to Item to find variants using this
		# attribute. Exercises the converted query builder version on both engines and asserts it
		# finds the variant (the raise only fires if the query returned the variant row).
		from erpnext.controllers.item_variant import InvalidItemAttributeValueError, create_variant

		frappe.delete_doc_if_exists("Item", "_Test Variant Item-L", force=1)
		variant = create_variant("_Test Variant Item", {"Test Size": "Large"})
		variant.save()

		attribute = frappe.get_doc("Item Attribute", "Test Size")
		attribute.item_attribute_values = []
		frappe.flags.attribute_values = None

		# "Large" is no longer a permitted value, so the variant found by validate_exising_items
		# is invalid; the save must abort (and so never persists the cleared values).
		self.assertRaises(InvalidItemAttributeValueError, attribute.save)

	def make_colour_template(self):
		from erpnext.stock.doctype.item.test_item import make_item

		if not frappe.db.exists("Item Attribute", "_Test Abbr Colour"):
			frappe.get_doc(
				{
					"doctype": "Item Attribute",
					"attribute_name": "_Test Abbr Colour",
					"item_attribute_values": [
						{"attribute_value": "Red", "abbr": "R"},
						{"attribute_value": "Blue", "abbr": "B"},
					],
				}
			).insert()

		return make_item(
			"_Test Abbr Template",
			{"has_variants": 1, "attributes": [{"attribute": "_Test Abbr Colour"}]},
		)

	def test_abbr_change_keeps_custom_variant_code(self):
		from erpnext.controllers.item_variant import create_variant

		template = self.make_colour_template()
		create_variant(template.name, {"_Test Abbr Colour": "Red"}).insert()
		custom = create_variant(template.name, {"_Test Abbr Colour": "Blue"})
		custom.item_code = "_Test Custom Blue SKU"
		custom.insert()

		attribute = frappe.get_doc("Item Attribute", "_Test Abbr Colour")
		for row in attribute.item_attribute_values:
			row.abbr = {"Red": "RD", "Blue": "BL"}[row.attribute_value]
		attribute.save()

		self.assertTrue(frappe.db.exists("Item", f"{template.name}-RD"))
		self.assertTrue(frappe.db.exists("Item", "_Test Custom Blue SKU"))
		self.assertFalse(frappe.db.exists("Item", f"{template.name}-BL"))

	def test_numeric_values_cannot_change_while_used_by_variants(self):
		from erpnext.controllers.item_variant import create_variant

		template = self.make_colour_template()
		create_variant(template.name, {"_Test Abbr Colour": "Red"}).insert()

		attribute = frappe.get_doc("Item Attribute", "_Test Abbr Colour")
		attribute.update({"numeric_values": 1, "from_range": 0, "to_range": 100, "increment": 1})
		self.assertRaises(frappe.ValidationError, attribute.save)
