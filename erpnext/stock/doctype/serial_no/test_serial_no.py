# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# ERPNext - web based ERP (http://erpnext.com)
# For license information, please see license.txt


import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.serial_no.serial_no import *
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_serialized_item
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

test_dependencies = ["Item"]
test_records = frappe.get_test_records("Serial No")


class TestSerialNo(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

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

		dn = create_delivery_note(
			item_code="_Test Serialized Item With Series", qty=1, serial_no=serial_nos[0]
		)

		serial_no = frappe.get_doc("Serial No", serial_nos[0])

		# check Serial No details after delivery
		self.assertEqual(serial_no.status, "Delivered")
		self.assertEqual(serial_no.warehouse, None)
		self.assertEqual(serial_no.company, "_Test Company")
		self.assertEqual(serial_no.delivery_document_type, "Delivery Note")
		self.assertEqual(serial_no.delivery_document_no, dn.name)

		wh = create_warehouse("_Test Warehouse", company="_Test Company 1")
		pr = make_purchase_receipt(
			item_code="_Test Serialized Item With Series",
			qty=1,
			serial_no=serial_nos[0],
			company="_Test Company 1",
			warehouse=wh,
		)

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

		dn = create_delivery_note(
			item_code="_Test Serialized Item With Series", qty=1, serial_no=serial_nos[0]
		)
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
		pr = make_purchase_receipt(
			item_code="_Test Serialized Item With Series",
			qty=1,
			serial_no=serial_nos[0],
			company="_Test Company 1",
			warehouse=wh,
		)
		sn_doc.reload()

		self.assertEqual(sn_doc.warehouse, wh)
		# try cancelling the delivery from the first company
		# block cancellation as Serial No belongs to different company
		self.assertRaises(frappe.ValidationError, dn.cancel)

		# deliver from second company
		dn_2 = create_delivery_note(
			item_code="_Test Serialized Item With Series",
			qty=1,
			serial_no=serial_nos[0],
			company="_Test Company 1",
			warehouse=wh,
		)
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
		dn = create_delivery_note(
			item_code="_Test Serialized Item With Series", qty=1, serial_no=serial_nos[0]
		)

		# Receipt in **second** company
		wh = create_warehouse("_Test Warehouse", company="_Test Company 1")
		pr = make_purchase_receipt(
			item_code="_Test Serialized Item With Series",
			qty=1,
			serial_no=serial_nos[0],
			company="_Test Company 1",
			warehouse=wh,
		)

		# Delivery from second company
		dn_2 = create_delivery_note(
			item_code="_Test Serialized Item With Series",
			qty=1,
			serial_no=serial_nos[0],
			company="_Test Company 1",
			warehouse=wh,
		)
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

	def test_auto_creation_of_serial_no(self):
		"""
		Test if auto created Serial No excludes existing serial numbers
		"""
		item_code = make_item(
			"_Test Auto Serial Item ", {"has_serial_no": 1, "serial_no_series": "XYZ.###"}
		).item_code

		# Reserve XYZ005
		pr_1 = make_purchase_receipt(item_code=item_code, qty=1, serial_no="XYZ005")
		# XYZ005 is already used and will throw an error if used again
		pr_2 = make_purchase_receipt(item_code=item_code, qty=10)

		self.assertEqual(get_serial_nos(pr_1.get("items")[0].serial_no)[0], "XYZ005")
		for serial_no in get_serial_nos(pr_2.get("items")[0].serial_no):
			self.assertNotEqual(serial_no, "XYZ005")

	def test_serial_no_sanitation(self):
		"Test if Serial No input is sanitised before entering the DB."
		item_code = "_Test Serialized Item"
		test_records = frappe.get_test_records("Stock Entry")

		se = frappe.copy_doc(test_records[0])
		se.get("items")[0].item_code = item_code
		se.get("items")[0].qty = 4
		se.get("items")[0].serial_no = " _TS1, _TS2 , _TS3  , _TS4 - 2021"
		se.get("items")[0].transfer_qty = 4
		se.set_stock_entry_type()
		se.insert()
		se.submit()

		self.assertEqual(se.get("items")[0].serial_no, "_TS1\n_TS2\n_TS3\n_TS4 - 2021")

	def test_correct_serial_no_incoming_rate(self):
		"""Check correct consumption rate based on serial no record."""
		item_code = "_Test Serialized Item"
		warehouse = "_Test Warehouse - _TC"
		serial_nos = ["LOWVALUATION", "HIGHVALUATION"]

		in1 = make_stock_entry(
			item_code=item_code, to_warehouse=warehouse, qty=1, rate=42, serial_no=serial_nos[0]
		)
		in2 = make_stock_entry(
			item_code=item_code, to_warehouse=warehouse, qty=1, rate=113, serial_no=serial_nos[1]
		)

		out = create_delivery_note(
			item_code=item_code, qty=1, serial_no=serial_nos[0], do_not_submit=True
		)

		# change serial no
		out.items[0].serial_no = serial_nos[1]
		out.save()
		out.submit()

		value_diff = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_no": out.name, "voucher_type": "Delivery Note"},
			"stock_value_difference",
		)
		self.assertEqual(value_diff, -113)

	def test_auto_fetch(self):
		item_code = make_item(
			properties={
				"has_serial_no": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"serial_no_series": "TEST.#######",
			}
		).name
		warehouse = "_Test Warehouse - _TC"

		in1 = make_stock_entry(item_code=item_code, to_warehouse=warehouse, qty=5)
		in2 = make_stock_entry(item_code=item_code, to_warehouse=warehouse, qty=5)

		in1.reload()
		in2.reload()

		batch1 = in1.items[0].batch_no
		batch2 = in2.items[0].batch_no

		batch_wise_serials = {
			batch1: get_serial_nos(in1.items[0].serial_no),
			batch2: get_serial_nos(in2.items[0].serial_no),
		}

		# Test FIFO
		first_fetch = auto_fetch_serial_number(5, item_code, warehouse)
		self.assertEqual(first_fetch, batch_wise_serials[batch1])

		# partial FIFO
		partial_fetch = auto_fetch_serial_number(2, item_code, warehouse)
		self.assertTrue(
			set(partial_fetch).issubset(set(first_fetch)),
			msg=f"{partial_fetch} should be subset of {first_fetch}",
		)

		# exclusion
		remaining = auto_fetch_serial_number(
			3, item_code, warehouse, exclude_sr_nos=json.dumps(partial_fetch)
		)
		self.assertEqual(sorted(remaining + partial_fetch), first_fetch)

		# batchwise
		for batch, expected_serials in batch_wise_serials.items():
			fetched_sr = auto_fetch_serial_number(5, item_code, warehouse, batch_nos=batch)
			self.assertEqual(fetched_sr, sorted(expected_serials))

		# non existing warehouse
		self.assertEqual(auto_fetch_serial_number(10, item_code, warehouse="Nonexisting"), [])

		# multi batch
		all_serials = [sr for sr_list in batch_wise_serials.values() for sr in sr_list]
		fetched_serials = auto_fetch_serial_number(
			10, item_code, warehouse, batch_nos=list(batch_wise_serials.keys())
		)
		self.assertEqual(sorted(all_serials), fetched_serials)

		# expiry date
		frappe.db.set_value("Batch", batch1, "expiry_date", "1980-01-01")
		non_expired_serials = auto_fetch_serial_number(
			5, item_code, warehouse, posting_date="2021-01-01", batch_nos=batch1
		)
		self.assertEqual(non_expired_serials, [])
