# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import unittest
import frappe

class TestItem(unittest.TestCase):
	def test_duplicate_item(self):
		from erpnext.stock.doctype.item_price.item_price import ItemPriceDuplicateItem
		doc = frappe.copy_doc(test_records[0])
		self.assertRaises(ItemPriceDuplicateItem, doc.save)

test_records = frappe.get_test_records('Item Price')