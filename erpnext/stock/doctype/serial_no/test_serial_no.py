# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# ERPNext - web based ERP (http://erpnext.com)
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe

from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_serialized_item
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

test_dependencies = ["Item"]
test_records = frappe.get_test_records('Serial No')

from erpnext.stock.doctype.serial_no.serial_no import *
from erpnext.tests.utils import ERPNextTestCase


class TestSerialNo(ERPNextTestCase):
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

		dn = create_delivery_note(item_code="_Test Serialized Item With Series", qty=1, serial_no=serial_nos[0])

		serial_no = frappe.get_doc("Serial No", serial_nos[0])

		# check Serial No details after delivery
		self.assertEqual(serial_no.status, "Delivered")
		self.assertEqual(serial_no.warehouse, None)
		self.assertEqual(serial_no.company, "_Test Company")
		self.assertEqual(serial_no.delivery_document_type, "Delivery Note")
		self.assertEqual(serial_no.delivery_document_no, dn.name)

		wh = create_warehouse("_Test Warehouse", company="_Test Company 1")
		pr = make_purchase_receipt(item_code="_Test Serialized Item With Series", qty=1, serial_no=serial_nos[0],
			company="_Test Company 1", warehouse=wh)

		serial_no.reload()

		# check Serial No details after purchase in second company
		self.assertEqual(serial_no.status, "Active")
		self.assertEqual(serial_no.warehouse, wh)
		self.assertEqual(serial_no.company, "_Test Company 1")
		self.assertEqual(serial_no.purchase_document_type, "Purchase Receipt")
		self.assertEqual(serial_no.purchase_document_no, pr.name)

	def test_inter_company_transfer_intermediate_cancellation(self):
		"""
			Receive into and Deliver Serial No from one company.
			Then Receive into and Deliver from second company.
			Try to cancel intermediate receipts/deliveries to test if it is blocked.
		"""
		se = make_serialized_item(target_warehouse="_Test Warehouse - _TC")
		serial_nos = get_serial_nos(se.get("items")[0].serial_no)

		sn_doc = frappe.get_doc("Serial No", serial_nos[0])

		# check Serial No details after purchase in first company
		self.assertEqual(sn_doc.status, "Active")
		self.assertEqual(sn_doc.company, "_Test Company")
		self.assertEqual(sn_doc.warehouse, "_Test Warehouse - _TC")
		self.assertEqual(sn_doc.purchase_document_no, se.name)

		dn = create_delivery_note(item_code="_Test Serialized Item With Series",
			qty=1, serial_no=serial_nos[0])
		sn_doc.reload()
		# check Serial No details after delivery from **first** company
		self.assertEqual(sn_doc.status, "Delivered")
		self.assertEqual(sn_doc.company, "_Test Company")
		self.assertEqual(sn_doc.warehouse, None)
		self.assertEqual(sn_doc.delivery_document_no, dn.name)

		# try cancelling the first Serial No Receipt, even though it is delivered
		# block cancellation is Serial No is out of the warehouse
		self.assertRaises(frappe.ValidationError, se.cancel)

		# receive serial no in second company
		wh = create_warehouse("_Test Warehouse", company="_Test Company 1")
		pr = make_purchase_receipt(item_code="_Test Serialized Item With Series",
			qty=1, serial_no=serial_nos[0], company="_Test Company 1", warehouse=wh)
		sn_doc.reload()

		self.assertEqual(sn_doc.warehouse, wh)
		# try cancelling the delivery from the first company
		# block cancellation as Serial No belongs to different company
		self.assertRaises(frappe.ValidationError, dn.cancel)

		# deliver from second company
		dn_2 = create_delivery_note(item_code="_Test Serialized Item With Series",
			qty=1, serial_no=serial_nos[0], company="_Test Company 1", warehouse=wh)
		sn_doc.reload()

		# check Serial No details after delivery from **second** company
		self.assertEqual(sn_doc.status, "Delivered")
		self.assertEqual(sn_doc.company, "_Test Company 1")
		self.assertEqual(sn_doc.warehouse, None)
		self.assertEqual(sn_doc.delivery_document_no, dn_2.name)

		# cannot cancel any intermediate document before last Delivery Note
		self.assertRaises(frappe.ValidationError, se.cancel)
		self.assertRaises(frappe.ValidationError, dn.cancel)
		self.assertRaises(frappe.ValidationError, pr.cancel)

	def test_inter_company_transfer_fallback_on_cancel(self):
		"""
			Test Serial No state changes on cancellation.
			If Delivery cancelled, it should fall back on last Receipt in the same company.
			If Receipt is cancelled, it should be Inactive in the same company.
		"""
		# Receipt in **first** company
		se = make_serialized_item(target_warehouse="_Test Warehouse - _TC")
		serial_nos = get_serial_nos(se.get("items")[0].serial_no)
		sn_doc = frappe.get_doc("Serial No", serial_nos[0])

		# Delivery from first company
		dn = create_delivery_note(item_code="_Test Serialized Item With Series",
			qty=1, serial_no=serial_nos[0])

		# Receipt in **second** company
		wh = create_warehouse("_Test Warehouse", company="_Test Company 1")
		pr = make_purchase_receipt(item_code="_Test Serialized Item With Series",
			qty=1, serial_no=serial_nos[0], company="_Test Company 1", warehouse=wh)

		# Delivery from second company
		dn_2 = create_delivery_note(item_code="_Test Serialized Item With Series",
			qty=1, serial_no=serial_nos[0], company="_Test Company 1", warehouse=wh)
		sn_doc.reload()

		self.assertEqual(sn_doc.status, "Delivered")
		self.assertEqual(sn_doc.company, "_Test Company 1")
		self.assertEqual(sn_doc.delivery_document_no, dn_2.name)

		dn_2.cancel()
		sn_doc.reload()
		# Fallback on Purchase Receipt if Delivery is cancelled
		self.assertEqual(sn_doc.status, "Active")
		self.assertEqual(sn_doc.company, "_Test Company 1")
		self.assertEqual(sn_doc.warehouse, wh)
		self.assertEqual(sn_doc.purchase_document_no, pr.name)

		pr.cancel()
		sn_doc.reload()
		# Inactive in same company if Receipt cancelled
		self.assertEqual(sn_doc.status, "Inactive")
		self.assertEqual(sn_doc.company, "_Test Company 1")
		self.assertEqual(sn_doc.warehouse, None)

		dn.cancel()
		sn_doc.reload()
		# Fallback on Purchase Receipt in FIRST company if
		# Delivery from FIRST company is cancelled
		self.assertEqual(sn_doc.status, "Active")
		self.assertEqual(sn_doc.company, "_Test Company")
		self.assertEqual(sn_doc.warehouse, "_Test Warehouse - _TC")
		self.assertEqual(sn_doc.purchase_document_no, se.name)

	def test_serial_no_sanitation(self):
		"Test if Serial No input is sanitised before entering the DB."
		item_code = "_Test Serialized Item"
		test_records = frappe.get_test_records('Stock Entry')

		se = frappe.copy_doc(test_records[0])
		se.get("items")[0].item_code = item_code
		se.get("items")[0].qty = 4
		se.get("items")[0].serial_no = " _TS1, _TS2 , _TS3  , _TS4 - 2021"
		se.get("items")[0].transfer_qty = 4
		se.set_stock_entry_type()
		se.insert()
		se.submit()

		self.assertEqual(se.get("items")[0].serial_no, "_TS1\n_TS2\n_TS3\n_TS4 - 2021")

		frappe.db.rollback()

	def tearDown(self):
		frappe.db.rollback()
