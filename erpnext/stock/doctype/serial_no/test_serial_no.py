# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# ERPNext - web based ERP (http://erpnext.com)
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, unittest

test_dependencies = ["Item"]
test_records = frappe.get_test_records('Serial No')

from erpnext.stock.doctype.serial_no.serial_no import *

class TestSerialNo(unittest.TestCase):
	def test_cannot_create_direct(self):
		frappe.delete_doc_if_exists("Serial No", "_TCSER0001")

		sr = frappe.new_doc("Serial No")
		sr.item_code = "_Test Serialized Item"
		sr.warehouse = "_Test Warehouse - _TC"
		sr.serial_no = "_TCSER0001"
		sr.purchase_rate = 10
		self.assertRaises(SerialNoCannotCreateDirectError, sr.insert)

		sr.warehouse = None
		sr.insert()
		self.assertTrue(sr.name)

		sr.warehouse = "_Test Warehouse - _TC"
		self.assertTrue(SerialNoCannotCannotChangeError, sr.save)
