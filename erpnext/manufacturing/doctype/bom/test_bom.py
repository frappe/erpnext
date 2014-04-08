# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import frappe

test_records = frappe.get_test_records('Bom')

class TestBOM(unittest.TestCase):
	def test_get_items(self):
		from erpnext.manufacturing.doctype.bom.bom import get_bom_items_as_dict
		items_dict = get_bom_items_as_dict(bom="BOM/_Test FG Item 2/001", qty=1, fetch_exploded=0)
		self.assertTrue(test_records[2]["bom_materials"][0]["item_code"] in items_dict)
		self.assertTrue(test_records[2]["bom_materials"][1]["item_code"] in items_dict)
		self.assertEquals(len(items_dict.values()), 2)

	def test_get_items_exploded(self):
		from erpnext.manufacturing.doctype.bom.bom import get_bom_items_as_dict
		items_dict = get_bom_items_as_dict(bom="BOM/_Test FG Item 2/001", qty=1, fetch_exploded=1)
		self.assertTrue(test_records[2]["bom_materials"][0]["item_code"] in items_dict)
		self.assertFalse(test_records[2]["bom_materials"][1]["item_code"] in items_dict)
		self.assertTrue(test_records[0]["bom_materials"][0]["item_code"] in items_dict)
		self.assertTrue(test_records[0]["bom_materials"][1]["item_code"] in items_dict)
		self.assertEquals(len(items_dict.values()), 3)

	def test_get_items_list(self):
		from erpnext.manufacturing.doctype.bom.bom import get_bom_items
		self.assertEquals(len(get_bom_items(bom="BOM/_Test FG Item 2/001", qty=1, fetch_exploded=1)), 3)
