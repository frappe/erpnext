# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

test_records = [
	[{
		"doctype": "Warehouse",
		"warehouse_name": "_Test Warehouse",
		"company": "_Test Company", 
		"create_account_under": "Stock Assets - _TC"
	}],
	[{
		"doctype": "Warehouse",
		"warehouse_name": "_Test Warehouse 1",
		"company": "_Test Company",
		"create_account_under": "Fixed Assets - _TC"
	}],
	[{
		"doctype": "Warehouse",
		"warehouse_name": "_Test Warehouse 2",
		"create_account_under": "Stock Assets - _TC",
		"company": "_Test Company 1"
	}, {
		"doctype": "Warehouse User",
		"parentfield": "warehouse_users",
		"user": "test2@example.com"
	}],
	[{
		"doctype": "Warehouse",
		"warehouse_name": "_Test Warehouse No Account",
		"company": "_Test Company",
	}],
]
