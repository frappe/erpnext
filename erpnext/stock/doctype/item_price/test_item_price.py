# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import unittest
import frappe

class TestItem(unittest.TestCase):
	def test_duplicate_item(self):
		from erpnext.stock.doctype.item_price.item_price import ItemPriceDuplicateItem
		bean = frappe.get_doc(copy=test_records[0])
		self.assertRaises(ItemPriceDuplicateItem, bean.insert)

test_records = [
	[
		{
			"doctype": "Item Price",
			"price_list": "_Test Price List",
			"item_code": "_Test Item",
			"price_list_rate": 100
		}
	]
]