# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

test_records = [
	[{
		"doctype": "Territory",
		"territory_name": "_Test Territory",
		"parent_territory": "All Territories",
		"is_group": "No",
	}],
	[{
		"doctype": "Territory",
		"territory_name": "_Test Territory India",
		"parent_territory": "All Territories",
		"is_group": "Yes",
	}],
	[{
		"doctype": "Territory",
		"territory_name": "_Test Territory Maharashtra",
		"parent_territory": "_Test Territory India",
		"is_group": "No",
	}],
	[{
		"doctype": "Territory",
		"territory_name": "_Test Territory Rest of the World",
		"parent_territory": "All Territories",
		"is_group": "No",
	}],
	[{
		"doctype": "Territory",
		"territory_name": "_Test Territory United States",
		"parent_territory": "All Territories",
		"is_group": "No",
	}],
]