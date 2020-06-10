# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt

from __future__ import unicode_literals
import frappe
import unittest

test_records = frappe.get_test_records('Item Attribute')

from erpnext.stock.doctype.item_attribute.item_attribute import ItemAttributeIncrementError

class TestItemAttribute(unittest.TestCase):
	def setUp(self):
		if frappe.db.exists("Item Attribute", "_Test_Length"):
			frappe.delete_doc("Item Attribute", "_Test_Length")

	def test_numeric_item_attribute(self):
		item_attribute = frappe.get_doc({
			"doctype": "Item Attribute",
			"attribute_name": "_Test_Length",
			"numeric_values": 1,
			"from_range": 0.0,
			"to_range": 100.0,
			"increment": 0
		})

		self.assertRaises(ItemAttributeIncrementError, item_attribute.save)

		item_attribute.increment = 0.5
		item_attribute.save()

