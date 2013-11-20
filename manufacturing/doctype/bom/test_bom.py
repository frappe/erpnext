# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import webnotes

test_records = [
	[
		{
			"doctype": "BOM", 
			"item": "_Test Item Home Desktop Manufactured", 
			"quantity": 1.0,
			"is_active": 1,
			"is_default": 1,
			"docstatus": 1
		}, 
		{
			"doctype": "BOM Item", 
			"item_code": "_Test Serialized Item With Series", 
			"parentfield": "bom_materials", 
			"qty": 1.0, 
			"rate": 5000.0, 
			"amount": 5000.0, 
			"stock_uom": "_Test UOM"
		}, 
		{
			"doctype": "BOM Item", 
			"item_code": "_Test Item 2", 
			"parentfield": "bom_materials", 
			"qty": 2.0, 
			"rate": 1000.0,
			"amount": 2000.0,
			"stock_uom": "_Test UOM"
		}
	],

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
	],
	
	[
		{
			"doctype": "BOM", 
			"item": "_Test FG Item 2", 
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
			"item_code": "_Test Item Home Desktop Manufactured", 
			"bom_no": "BOM/_Test Item Home Desktop Manufactured/001",
			"parentfield": "bom_materials", 
			"qty": 2.0, 
			"rate": 1000.0,
			"amount": 2000.0,
			"stock_uom": "_Test UOM"
		}
	],
]

class TestBOM(unittest.TestCase):
	def test_get_items(self):
		from manufacturing.doctype.bom.bom import get_bom_items_as_dict
		items_dict = get_bom_items_as_dict(bom="BOM/_Test FG Item 2/001", qty=1, fetch_exploded=0)
		self.assertTrue(test_records[2][1]["item_code"] in items_dict)
		self.assertTrue(test_records[2][2]["item_code"] in items_dict)
		self.assertEquals(len(items_dict.values()), 2)
		
	def test_get_items_exploded(self):
		from manufacturing.doctype.bom.bom import get_bom_items_as_dict
		items_dict = get_bom_items_as_dict(bom="BOM/_Test FG Item 2/001", qty=1, fetch_exploded=1)
		self.assertTrue(test_records[2][1]["item_code"] in items_dict)
		self.assertFalse(test_records[2][2]["item_code"] in items_dict)
		self.assertTrue(test_records[0][1]["item_code"] in items_dict)
		self.assertTrue(test_records[0][2]["item_code"] in items_dict)
		self.assertEquals(len(items_dict.values()), 3)
		
	def test_get_items_list(self):
		from manufacturing.doctype.bom.bom import get_bom_items
		self.assertEquals(len(get_bom_items(bom="BOM/_Test FG Item 2/001", qty=1, fetch_exploded=1)), 3)

