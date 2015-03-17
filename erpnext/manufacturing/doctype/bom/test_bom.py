# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import frappe
from frappe.utils import cstr

test_records = frappe.get_test_records('BOM')

class TestBOM(unittest.TestCase):
	def test_get_items(self):
		from erpnext.manufacturing.doctype.bom.bom import get_bom_items_as_dict
		items_dict = get_bom_items_as_dict(bom="BOM/_Test FG Item 2/001", qty=1, fetch_exploded=0)
		self.assertTrue(test_records[2]["items"][0]["item_code"] in items_dict)
		self.assertTrue(test_records[2]["items"][1]["item_code"] in items_dict)
		self.assertEquals(len(items_dict.values()), 2)

	def test_get_items_exploded(self):
		from erpnext.manufacturing.doctype.bom.bom import get_bom_items_as_dict
		items_dict = get_bom_items_as_dict(bom="BOM/_Test FG Item 2/001", qty=1, fetch_exploded=1)
		self.assertTrue(test_records[2]["items"][0]["item_code"] in items_dict)
		self.assertFalse(test_records[2]["items"][1]["item_code"] in items_dict)
		self.assertTrue(test_records[0]["items"][0]["item_code"] in items_dict)
		self.assertTrue(test_records[0]["items"][1]["item_code"] in items_dict)
		self.assertEquals(len(items_dict.values()), 3)

	def test_get_items_list(self):
		from erpnext.manufacturing.doctype.bom.bom import get_bom_items
		default_bom = frappe.db.get_value("BOM", {"item":"_Test FG Item 2", "is_default": 1})
		self.assertEquals(len(get_bom_items(bom=default_bom)), 3)

	def test_default_bom(self):
		def _get_default_bom_in_item():
			return cstr(frappe.db.get_value("Item", "_Test FG Item 2", "default_bom"))

		bom = frappe.get_doc("BOM", {"item":"_Test FG Item 2", "is_default": 1})
		self.assertEqual(_get_default_bom_in_item(), bom.name)

		bom.is_active = 0
		bom.save()
		self.assertEqual(_get_default_bom_in_item(), "")

		bom.is_active = 1
		bom.is_default=1
		bom.save()

		self.assertTrue(_get_default_bom_in_item(), bom.name)
