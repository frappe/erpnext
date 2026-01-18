# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# ERPNext - web based ERP (http://erpnext.com)
# For license information, please see license.txt


import frappe
from frappe import _dict
from frappe.tests import IntegrationTestCase

from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.serial_and_batch_bundle.test_serial_and_batch_bundle import (
	get_batch_from_bundle,
	get_serial_nos_from_bundle,
)
from erpnext.stock.doctype.serial_no.serial_no import *
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_serialized_item
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

EXTRA_TEST_RECORD_DEPENDENCIES = ["Item"]


class TestSerialNo(IntegrationTestCase):
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
		se = make_serialized_item(self, target_warehouse="_Test Warehouse - _TC")
		serial_nos = get_serial_nos_from_bundle(se.get("items")[0].serial_and_batch_bundle)

		create_delivery_note(item_code="_Test Serialized Item With Series", qty=1, serial_no=[serial_nos[0]])

		serial_no = frappe.get_doc("Serial No", serial_nos[0])

		# check Serial No details after delivery
		self.assertEqual(serial_no.warehouse, None)

		wh = create_warehouse("_Test Warehouse", company="_Test Company 1")
		make_purchase_receipt(
			item_code="_Test Serialized Item With Series",
			qty=1,
			serial_no=[serial_nos[0]],
			company="_Test Company 1",
			warehouse=wh,
		)

		serial_no.reload()

		# check Serial No details after purchase in second company
		self.assertEqual(serial_no.warehouse, wh)

	def test_inter_company_transfer_intermediate_cancellation(self):
		"""
		Receive into and Deliver Serial No from one company.
		Then Receive into and Deliver from second company.
		Try to cancel intermediate receipts/deliveries to test if it is blocked.
		"""
		se = make_serialized_item(self, target_warehouse="_Test Warehouse - _TC")
		serial_nos = get_serial_nos_from_bundle(se.get("items")[0].serial_and_batch_bundle)

		sn_doc = frappe.get_doc("Serial No", serial_nos[0])

		# check Serial No details after purchase in first company
		self.assertEqual(sn_doc.warehouse, "_Test Warehouse - _TC")

		dn = create_delivery_note(
			item_code="_Test Serialized Item With Series", qty=1, serial_no=[serial_nos[0]]
		)
		sn_doc.reload()
		# check Serial No details after delivery from **first** company
		self.assertEqual(sn_doc.warehouse, None)

		# try cancelling the first Serial No Receipt, even though it is delivered
		# block cancellation is Serial No is out of the warehouse
		self.assertRaises(frappe.ValidationError, se.cancel)

		# receive serial no in second company
		wh = create_warehouse("_Test Warehouse", company="_Test Company 1")
		pr = make_purchase_receipt(
			item_code="_Test Serialized Item With Series",
			qty=1,
			serial_no=[serial_nos[0]],
			company="_Test Company 1",
			warehouse=wh,
		)
		sn_doc.reload()

		self.assertEqual(sn_doc.warehouse, wh)
		# try cancelling the delivery from the first company
		# block cancellation as Serial No belongs to different company
		self.assertRaises(frappe.ValidationError, dn.cancel)

		# deliver from second company
		create_delivery_note(
			item_code="_Test Serialized Item With Series",
			qty=1,
			serial_no=[serial_nos[0]],
			company="_Test Company 1",
			warehouse=wh,
			cost_center="_Test Company 1 - _TC1",
		)
		sn_doc.reload()

		# check Serial No details after delivery from **second** company
		self.assertEqual(sn_doc.warehouse, None)

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
		se = make_serialized_item(self, target_warehouse="_Test Warehouse - _TC")
		serial_nos = get_serial_nos_from_bundle(se.get("items")[0].serial_and_batch_bundle)
		sn_doc = frappe.get_doc("Serial No", serial_nos[0])

		# Delivery from first company
		dn = create_delivery_note(
			item_code="_Test Serialized Item With Series", qty=1, serial_no=[serial_nos[0]]
		)

		# Receipt in **second** company
		wh = create_warehouse("_Test Warehouse", company="_Test Company 1")
		pr = make_purchase_receipt(
			item_code="_Test Serialized Item With Series",
			qty=1,
			serial_no=[serial_nos[0]],
			company="_Test Company 1",
			warehouse=wh,
			cost_center="_Test Company 1 - _TC1",
		)

		# Delivery from second company
		dn_2 = create_delivery_note(
			item_code="_Test Serialized Item With Series",
			qty=1,
			serial_no=[serial_nos[0]],
			company="_Test Company 1",
			warehouse=wh,
			cost_center="_Test Company 1 - _TC1",
		)
		sn_doc.reload()

		self.assertEqual(sn_doc.warehouse, None)

		dn_2.cancel()
		sn_doc.reload()
		# Fallback on Purchase Receipt if Delivery is cancelled
		self.assertEqual(sn_doc.warehouse, wh)

		pr.cancel()
		sn_doc.reload()
		# Inactive in same company if Receipt cancelled
		self.assertEqual(sn_doc.warehouse, None)

		dn.cancel()
		sn_doc.reload()
		# Fallback on Purchase Receipt in FIRST company if
		# Delivery from FIRST company is cancelled
		self.assertEqual(sn_doc.warehouse, "_Test Warehouse - _TC")

	def test_correct_serial_no_incoming_rate(self):
		"""Check correct consumption rate based on serial no record."""
		item_code = "_Test Serialized Item"
		warehouse = "_Test Warehouse - _TC"
		serial_nos = ["LOWVALUATION", "HIGHVALUATION"]

		for serial_no in serial_nos:
			if not frappe.db.exists("Serial No", serial_no):
				frappe.get_doc(
					{"doctype": "Serial No", "item_code": item_code, "serial_no": serial_no}
				).insert()

		make_stock_entry(
			item_code=item_code, to_warehouse=warehouse, qty=1, rate=42, serial_no=[serial_nos[0]]
		)
		make_stock_entry(
			item_code=item_code, to_warehouse=warehouse, qty=1, rate=113, serial_no=[serial_nos[1]]
		)

		out = create_delivery_note(item_code=item_code, qty=1, serial_no=[serial_nos[0]], do_not_submit=True)

		bundle = out.items[0].serial_and_batch_bundle
		doc = frappe.get_doc("Serial and Batch Bundle", bundle)
		doc.entries[0].serial_no = serial_nos[1]
		doc.save()

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

		batch1 = get_batch_from_bundle(in1.items[0].serial_and_batch_bundle)
		batch2 = get_batch_from_bundle(in2.items[0].serial_and_batch_bundle)

		batch_wise_serials = {
			batch1: get_serial_nos_from_bundle(in1.items[0].serial_and_batch_bundle),
			batch2: get_serial_nos_from_bundle(in2.items[0].serial_and_batch_bundle),
		}

		# Test FIFO
		first_fetch = get_auto_serial_nos(
			_dict(
				{
					"qty": 5,
					"item_code": item_code,
					"warehouse": warehouse,
				}
			)
		)

		self.assertEqual(first_fetch, batch_wise_serials[batch1])

		# partial FIFO
		partial_fetch = get_auto_serial_nos(
			_dict(
				{
					"qty": 2,
					"item_code": item_code,
					"warehouse": warehouse,
				}
			)
		)

		self.assertTrue(
			set(partial_fetch).issubset(set(first_fetch)),
			msg=f"{partial_fetch} should be subset of {first_fetch}",
		)

		# exclusion
		remaining = get_auto_serial_nos(
			_dict(
				{
					"qty": 3,
					"item_code": item_code,
					"warehouse": warehouse,
					"ignore_serial_nos": partial_fetch,
				}
			)
		)

		self.assertEqual(sorted(remaining + partial_fetch), first_fetch)

		# batchwise
		for batch, expected_serials in batch_wise_serials.items():
			fetched_sr = get_auto_serial_nos(
				_dict({"qty": 5, "item_code": item_code, "warehouse": warehouse, "batches": [batch]})
			)

			self.assertEqual(fetched_sr, sorted(expected_serials))

		# non existing warehouse
		self.assertFalse(
			get_auto_serial_nos(
				_dict({"qty": 10, "item_code": item_code, "warehouse": "Non Existing Warehouse"})
			)
		)

		# multi batch
		all_serials = [sr for sr_list in batch_wise_serials.values() for sr in sr_list]
		fetched_serials = get_auto_serial_nos(
			_dict(
				{
					"qty": 10,
					"item_code": item_code,
					"warehouse": warehouse,
					"batches": list(batch_wise_serials.keys()),
				}
			)
		)
		self.assertEqual(sorted(all_serials), fetched_serials)

		# expiry date
		frappe.db.set_value("Batch", batch1, "expiry_date", "1980-01-01")
		non_expired_serials = get_auto_serial_nos(
			_dict({"qty": 5, "item_code": item_code, "warehouse": warehouse, "batches": [batch1]})
		)

		self.assertEqual(non_expired_serials, [])


def get_auto_serial_nos(kwargs):
	from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
		get_available_serial_nos,
	)

	serial_nos = get_available_serial_nos(kwargs)
	return sorted([d.serial_no for d in serial_nos])
