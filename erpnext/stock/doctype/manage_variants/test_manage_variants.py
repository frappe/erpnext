# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import unittest
import frappe

from erpnext.stock.doctype.manage_variants.manage_variants import DuplicateAttribute

class TestManageVariants(unittest.TestCase):
	def test_variant_item_codes(self):
		manage_variant = frappe.new_doc("Manage Variants")
		manage_variant.update({
			"item_code": "_Test Variant Item",
			"attributes": [
				{
					"attribute": "Test Size",
					"attribute_value": "Small"
				},
				{
					"attribute": "Test Size",
					"attribute_value": "Large"
				}
			]
		})
		manage_variant.generate_combinations()
		self.assertEqual(manage_variant.variants[0].variant, "_Test Variant Item-S")
		self.assertEqual(manage_variant.variants[1].variant, "_Test Variant Item-L")
		
		self.assertEqual(manage_variant.variants[0].variant_attributes, "Small")
		self.assertEqual(manage_variant.variants[1].variant_attributes, "Large")
		manage_variant.create_variants()

	def test_attributes_are_unique(self):
		manage_variant = frappe.new_doc("Manage Variants")
		manage_variant.update({
			"item_code": "_Test Variant Item",
			"attributes": [
				{
					"attribute": "Test Size",
					"attribute_value": "Small"
				},
				{
					"attribute": "Test Size",
					"attribute_value": "Small"
				}
			]
		})
		self.assertRaises(DuplicateAttribute, manage_variant.generate_combinations)
