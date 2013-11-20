# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

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
			"doctype": "Applicable Territory",
			"parentfield": "valid_for_territories",
			"territory": "All Territories"
		},
	],
	[
		{
			"doctype": "Price List",
			"price_list_name": "_Test Price List 2",
			"currency": "INR",
			"buying_or_selling": "Selling"
		},
		{
			"doctype": "Applicable Territory",
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
			"doctype": "Applicable Territory",
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
			"doctype": "Applicable Territory",
			"parentfield": "valid_for_territories",
			"territory": "_Test Territory Rest of the World"
		},
		{
			"doctype": "Applicable Territory",
			"parentfield": "valid_for_territories",
			"territory": "_Test Territory United States"
		}
	],
]