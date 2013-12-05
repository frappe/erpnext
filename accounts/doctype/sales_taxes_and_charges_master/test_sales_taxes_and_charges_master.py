# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

test_records = [
	[
		{
			"doctype": "Sales Taxes and Charges Master",
			"title": "_Test Sales Taxes and Charges Master",
			"company": "_Test Company"
		},
		{
			"account_head": "_Test Account VAT - _TC", 
			"charge_type": "On Net Total", 
			"description": "VAT", 
			"doctype": "Sales Taxes and Charges", 
			"parentfield": "other_charges",
			"rate": 6,
		}, 
		{
			"account_head": "_Test Account Service Tax - _TC", 
			"charge_type": "On Net Total", 
			"description": "Service Tax", 
			"doctype": "Sales Taxes and Charges", 
			"parentfield": "other_charges",
			"rate": 6.36,
		},
		{
			"doctype": "Applicable Territory",
			"parentfield": "valid_for_territories",
			"territory": "All Territories"
		}
	],
	[
		{
			"doctype": "Sales Taxes and Charges Master",
			"title": "_Test India Tax Master",
			"company": "_Test Company"
		},
		{
			"doctype": "Sales Taxes and Charges",
			"parentfield": "other_charges",
			"charge_type": "Actual",
			"account_head": "_Test Account Shipping Charges - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"description": "Shipping Charges",
			"rate": 100
		},
		{
			"doctype": "Sales Taxes and Charges",
			"parentfield": "other_charges",
			"charge_type": "On Net Total",
			"account_head": "_Test Account Customs Duty - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"description": "Customs Duty",
			"rate": 10
		},
		{
			"doctype": "Sales Taxes and Charges",
			"parentfield": "other_charges",
			"charge_type": "On Net Total",
			"account_head": "_Test Account Excise Duty - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"description": "Excise Duty",
			"rate": 12
		},
		{
			"doctype": "Sales Taxes and Charges",
			"parentfield": "other_charges",
			"charge_type": "On Previous Row Amount",
			"account_head": "_Test Account Education Cess - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"description": "Education Cess",
			"rate": 2,
			"row_id": 3
		},
		{
			"doctype": "Sales Taxes and Charges",
			"parentfield": "other_charges",
			"charge_type": "On Previous Row Amount",
			"account_head": "_Test Account S&H Education Cess - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"description": "S&H Education Cess",
			"rate": 1,
			"row_id": 3
		},
		{
			"doctype": "Sales Taxes and Charges",
			"parentfield": "other_charges",
			"charge_type": "On Previous Row Total",
			"account_head": "_Test Account CST - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"description": "CST",
			"rate": 2,
			"row_id": 5
		},
		{
			"doctype": "Sales Taxes and Charges",
			"parentfield": "other_charges",
			"charge_type": "On Net Total",
			"account_head": "_Test Account VAT - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"description": "VAT",
			"rate": 12.5
		},
		{
			"doctype": "Sales Taxes and Charges",
			"parentfield": "other_charges",
			"charge_type": "On Previous Row Total",
			"account_head": "_Test Account Discount - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"description": "Discount",
			"rate": -10,
			"row_id": 7
		},
		{
			"doctype": "Applicable Territory",
			"parentfield": "valid_for_territories",
			"territory": "_Test Territory India"
		}
	],
	[
		{
			"doctype": "Sales Taxes and Charges Master",
			"title": "_Test Sales Taxes and Charges Master 2",
			"company": "_Test Company"
		},
		{
			"account_head": "_Test Account VAT - _TC", 
			"charge_type": "On Net Total", 
			"description": "VAT", 
			"doctype": "Sales Taxes and Charges", 
			"parentfield": "other_charges",
			"rate": 12,
		}, 
		{
			"account_head": "_Test Account Service Tax - _TC", 
			"charge_type": "On Net Total", 
			"description": "Service Tax", 
			"doctype": "Sales Taxes and Charges", 
			"parentfield": "other_charges",
			"rate": 4,
		},
		{
			"doctype": "Applicable Territory",
			"parentfield": "valid_for_territories",
			"territory": "All Territories"
		}
	],
]