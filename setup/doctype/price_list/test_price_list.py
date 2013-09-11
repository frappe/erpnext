# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import unittest
import webnotes
from setup.doctype.price_list.price_list import PriceListDuplicateItem

class TestItem(unittest.TestCase):
	def test_duplicate_item(self):
		price_list = webnotes.bean(copy=test_records[0])
		item_price = price_list.doclist.get({"doctype": "Item Price"})[0]
		price_list.doclist.append(webnotes.doc(item_price.fields.copy()))
		self.assertRaises(PriceListDuplicateItem, price_list.insert)

# test_ignore = ["Item"]

test_records = [
	[
		{
			"doctype": "Price List",
			"price_list_name": "_Test Price List",
			"currency": "INR",
			"buying_or_selling": "Selling"
		},
		{
			"doctype": "For Territory",
			"parentfield": "valid_for_territories",
			"territory": "All Territories"
		},
		{
			"doctype": "Item Price",
			"parentfield": "item_prices",
			"item_code": "_Test Item",
			"ref_rate": 100
		}
	],
	[
		{
			"doctype": "Price List",
			"price_list_name": "_Test Price List 2",
			"currency": "INR",
			"buying_or_selling": "Selling"
		},
		{
			"doctype": "For Territory",
			"parentfield": "valid_for_territories",
			"territory": "_Test Territory Rest of the World"
		}
	],
	[
		{
			"doctype": "Price List",
			"price_list_name": "_Test Price List India",
			"currency": "INR",
			"buying_or_selling": "Selling"
		},
		{
			"doctype": "For Territory",
			"parentfield": "valid_for_territories",
			"territory": "_Test Territory India"
		}
	],
	[
		{
			"doctype": "Price List",
			"price_list_name": "_Test Price List Rest of the World",
			"currency": "USD",
			"buying_or_selling": "Selling"
		},
		{
			"doctype": "For Territory",
			"parentfield": "valid_for_territories",
			"territory": "_Test Territory Rest of the World"
		},
		{
			"doctype": "For Territory",
			"parentfield": "valid_for_territories",
			"territory": "_Test Territory United States"
		}
	],
]