# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import unittest
import webnotes
from setup.doctype.item_price.item_price import ItemPriceDuplicateItem

class TestItem(unittest.TestCase):
	def test_duplicate_item(self):
		item_price = webnotes.bean(copy=test_records[0])
		self.assertRaises(ItemPriceDuplicateItem, item_price.insert)

test_records = [
	[
		{
			"doctype": "Item Price",
			"price_list": "_Test Price List",
			"item_code": "_Test Item",
			"ref_rate": 100
		}
	]
]