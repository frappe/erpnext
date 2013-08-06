# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import webnotes

test_records = [
	[
		{
			"doctype": "BOM", 
			"item": "_Test FG Item", 
			"quantity": 1.0,
			"is_active": 1,
			"is_default": 1,
			"docstatus": 1
		}, 
		{
			"doctype": "BOM Item", 
			"item_code": "_Test Item", 
			"parentfield": "bom_materials", 
			"qty": 1.0, 
			"rate": 5000.0, 
			"amount": 5000.0, 
			"stock_uom": "_Test UOM"
		}, 
		{
			"doctype": "BOM Item", 
			"item_code": "_Test Item Home Desktop 100", 
			"parentfield": "bom_materials", 
			"qty": 2.0, 
			"rate": 1000.0,
			"amount": 2000.0,
			"stock_uom": "_Test UOM"
		}
	]
]