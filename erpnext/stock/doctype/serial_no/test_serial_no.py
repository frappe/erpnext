# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# ERPNext - web based ERP (http://erpnext.com)
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, unittest

from erpnext.stock.doctype.stock_entry.test_stock_entry import make_serialized_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

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

	def test_inter_company_transfer(self):
		se = make_serialized_item(target_warehouse="_Test Warehouse - _TC")
		serial_nos = get_serial_nos(se.get("items")[0].serial_no)

		create_delivery_note(item_code="_Test Serialized Item With Series", qty=1, serial_no=serial_nos[0])

		wh = create_warehouse("_Test Warehouse", company="_Test Company 1")
		make_purchase_receipt(item_code="_Test Serialized Item With Series", qty=1, serial_no=serial_nos[0],
			company="_Test Company 1", warehouse=wh)

		serial_no = frappe.db.get_value("Serial No", serial_nos[0], ["warehouse", "company"], as_dict=1)

		self.assertEqual(serial_no.warehouse, wh)
		self.assertEqual(serial_no.company, "_Test Company 1")

	def tearDown(self):
		frappe.db.rollback()