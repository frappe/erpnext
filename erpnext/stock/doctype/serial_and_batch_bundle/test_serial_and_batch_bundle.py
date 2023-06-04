# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import json

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_to_date, flt, nowdate, nowtime, today

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry


class TestSerialandBatchBundle(FrappeTestCase):
	def test_inward_outward_serial_valuation(self):
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		serial_item_code = "New Serial No Valuation 1"
		make_item(
			serial_item_code,
			{
				"has_serial_no": 1,
				"serial_no_series": "TEST-SER-VAL-.#####",
				"is_stock_item": 1,
			},
		)

		pr = make_purchase_receipt(
			item_code=serial_item_code, warehouse="_Test Warehouse - _TC", qty=1, rate=500
		)

		serial_no1 = get_serial_nos_from_bundle(pr.items[0].serial_and_batch_bundle)[0]

		pr = make_purchase_receipt(
			item_code=serial_item_code, warehouse="_Test Warehouse - _TC", qty=1, rate=300
		)

		serial_no2 = get_serial_nos_from_bundle(pr.items[0].serial_and_batch_bundle)[0]

		dn = create_delivery_note(
			item_code=serial_item_code,
			warehouse="_Test Warehouse - _TC",
			qty=1,
			rate=1500,
			serial_no=[serial_no2],
		)

		stock_value_difference = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_no": dn.name, "is_cancelled": 0, "voucher_type": "Delivery Note"},
			"stock_value_difference",
		)

		self.assertEqual(flt(stock_value_difference, 2), -300)

		dn = create_delivery_note(
			item_code=serial_item_code,
			warehouse="_Test Warehouse - _TC",
			qty=1,
			rate=1500,
			serial_no=[serial_no1],
		)

		stock_value_difference = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_no": dn.name, "is_cancelled": 0, "voucher_type": "Delivery Note"},
			"stock_value_difference",
		)

		self.assertEqual(flt(stock_value_difference, 2), -500)

	def test_inward_outward_batch_valuation(self):
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		batch_item_code = "New Batch No Valuation 1"
		make_item(
			batch_item_code,
			{
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "TEST-BATTCCH-VAL-.#####",
				"is_stock_item": 1,
			},
		)

		pr = make_purchase_receipt(
			item_code=batch_item_code, warehouse="_Test Warehouse - _TC", qty=10, rate=500
		)

		batch_no1 = get_batch_from_bundle(pr.items[0].serial_and_batch_bundle)

		pr = make_purchase_receipt(
			item_code=batch_item_code, warehouse="_Test Warehouse - _TC", qty=10, rate=300
		)

		batch_no2 = get_batch_from_bundle(pr.items[0].serial_and_batch_bundle)

		dn = create_delivery_note(
			item_code=batch_item_code,
			warehouse="_Test Warehouse - _TC",
			qty=10,
			rate=1500,
			batch_no=batch_no2,
		)

		stock_value_difference = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_no": dn.name, "is_cancelled": 0, "voucher_type": "Delivery Note"},
			"stock_value_difference",
		)

		self.assertEqual(flt(stock_value_difference, 2), -3000)

		dn = create_delivery_note(
			item_code=batch_item_code,
			warehouse="_Test Warehouse - _TC",
			qty=10,
			rate=1500,
			batch_no=batch_no1,
		)

		stock_value_difference = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_no": dn.name, "is_cancelled": 0, "voucher_type": "Delivery Note"},
			"stock_value_difference",
		)

		self.assertEqual(flt(stock_value_difference, 2), -5000)

	def test_old_batch_valuation(self):
		frappe.flags.ignore_serial_batch_bundle_validation = True
		batch_item_code = "Old Batch Item Valuation 1"
		make_item(
			batch_item_code,
			{
				"has_batch_no": 1,
				"is_stock_item": 1,
			},
		)

		batch_id = "Old Batch 1"
		if not frappe.db.exists("Batch", batch_id):
			batch_doc = frappe.get_doc(
				{
					"doctype": "Batch",
					"batch_id": batch_id,
					"item": batch_item_code,
					"use_batchwise_valuation": 0,
				}
			).insert(ignore_permissions=True)

			self.assertTrue(batch_doc.use_batchwise_valuation)
			batch_doc.db_set("use_batchwise_valuation", 0)

		stock_queue = []
		qty_after_transaction = 0
		balance_value = 0
		for qty, valuation in {10: 100, 20: 200}.items():
			stock_queue.append([qty, valuation])
			qty_after_transaction += qty
			balance_value += qty_after_transaction * valuation

			doc = frappe.get_doc(
				{
					"doctype": "Stock Ledger Entry",
					"posting_date": today(),
					"posting_time": nowtime(),
					"batch_no": batch_id,
					"incoming_rate": valuation,
					"qty_after_transaction": qty_after_transaction,
					"stock_value_difference": valuation * qty,
					"balance_value": balance_value,
					"valuation_rate": balance_value / qty_after_transaction,
					"actual_qty": qty,
					"item_code": batch_item_code,
					"warehouse": "_Test Warehouse - _TC",
					"stock_queue": json.dumps(stock_queue),
				}
			)

			doc.flags.ignore_permissions = True
			doc.flags.ignore_mandatory = True
			doc.flags.ignore_links = True
			doc.flags.ignore_validate = True
			doc.submit()

		bundle_doc = make_serial_batch_bundle(
			{
				"item_code": batch_item_code,
				"warehouse": "_Test Warehouse - _TC",
				"voucher_type": "Stock Entry",
				"posting_date": today(),
				"posting_time": nowtime(),
				"qty": -10,
				"batches": frappe._dict({batch_id: 10}),
				"type_of_transaction": "Outward",
				"do_not_submit": True,
			}
		)

		bundle_doc.reload()
		for row in bundle_doc.entries:
			self.assertEqual(flt(row.stock_value_difference, 2), -1666.67)

		bundle_doc.flags.ignore_permissions = True
		bundle_doc.flags.ignore_mandatory = True
		bundle_doc.flags.ignore_links = True
		bundle_doc.flags.ignore_validate = True
		bundle_doc.submit()

		bundle_doc = make_serial_batch_bundle(
			{
				"item_code": batch_item_code,
				"warehouse": "_Test Warehouse - _TC",
				"voucher_type": "Stock Entry",
				"posting_date": today(),
				"posting_time": nowtime(),
				"qty": -20,
				"batches": frappe._dict({batch_id: 20}),
				"type_of_transaction": "Outward",
				"do_not_submit": True,
			}
		)

		bundle_doc.reload()
		for row in bundle_doc.entries:
			self.assertEqual(flt(row.stock_value_difference, 2), -3333.33)

		bundle_doc.flags.ignore_permissions = True
		bundle_doc.flags.ignore_mandatory = True
		bundle_doc.flags.ignore_links = True
		bundle_doc.flags.ignore_validate = True
		bundle_doc.submit()

		frappe.flags.ignore_serial_batch_bundle_validation = False

	def test_old_serial_no_valuation(self):
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		serial_no_item_code = "Old Serial No Item Valuation 1"
		make_item(
			serial_no_item_code,
			{
				"has_serial_no": 1,
				"serial_no_series": "TEST-SER-VALL-.#####",
				"is_stock_item": 1,
			},
		)

		make_purchase_receipt(
			item_code=serial_no_item_code, warehouse="_Test Warehouse - _TC", qty=1, rate=500
		)

		frappe.flags.ignore_serial_batch_bundle_validation = True

		serial_no_id = "Old Serial No 1"
		if not frappe.db.exists("Serial No", serial_no_id):
			sn_doc = frappe.get_doc(
				{
					"doctype": "Serial No",
					"serial_no": serial_no_id,
					"item_code": serial_no_item_code,
					"company": "_Test Company",
				}
			).insert(ignore_permissions=True)

			sn_doc.db_set(
				{
					"warehouse": "_Test Warehouse - _TC",
					"purchase_rate": 100,
				}
			)

		doc = frappe.get_doc(
			{
				"doctype": "Stock Ledger Entry",
				"posting_date": today(),
				"posting_time": nowtime(),
				"serial_no": serial_no_id,
				"incoming_rate": 100,
				"qty_after_transaction": 1,
				"stock_value_difference": 100,
				"balance_value": 100,
				"valuation_rate": 100,
				"actual_qty": 1,
				"item_code": serial_no_item_code,
				"warehouse": "_Test Warehouse - _TC",
				"company": "_Test Company",
			}
		)

		doc.flags.ignore_permissions = True
		doc.flags.ignore_mandatory = True
		doc.flags.ignore_links = True
		doc.flags.ignore_validate = True
		doc.submit()

		bundle_doc = make_serial_batch_bundle(
			{
				"item_code": serial_no_item_code,
				"warehouse": "_Test Warehouse - _TC",
				"voucher_type": "Stock Entry",
				"posting_date": today(),
				"posting_time": nowtime(),
				"qty": -1,
				"serial_nos": [serial_no_id],
				"type_of_transaction": "Outward",
				"do_not_submit": True,
			}
		)

		bundle_doc.reload()
		for row in bundle_doc.entries:
			self.assertEqual(flt(row.stock_value_difference, 2), -100.00)

	def test_batch_not_belong_to_serial_no(self):
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		serial_and_batch_code = "New Serial No Valuation 1"
		make_item(
			serial_and_batch_code,
			{
				"has_serial_no": 1,
				"serial_no_series": "TEST-SER-VALL-.#####",
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "TEST-SNBAT-VAL-.#####",
			},
		)

		pr = make_purchase_receipt(
			item_code=serial_and_batch_code, warehouse="_Test Warehouse - _TC", qty=1, rate=500
		)

		serial_no = get_serial_nos_from_bundle(pr.items[0].serial_and_batch_bundle)[0]

		pr = make_purchase_receipt(
			item_code=serial_and_batch_code, warehouse="_Test Warehouse - _TC", qty=1, rate=300
		)

		batch_no = get_batch_from_bundle(pr.items[0].serial_and_batch_bundle)

		doc = frappe.get_doc(
			{
				"doctype": "Serial and Batch Bundle",
				"item_code": serial_and_batch_code,
				"warehouse": "_Test Warehouse - _TC",
				"voucher_type": "Stock Entry",
				"posting_date": today(),
				"posting_time": nowtime(),
				"qty": -1,
				"type_of_transaction": "Outward",
			}
		)

		doc.append(
			"entries",
			{
				"batch_no": batch_no,
				"serial_no": serial_no,
				"qty": -1,
			},
		)

		# Batch does not belong to serial no
		self.assertRaises(frappe.exceptions.ValidationError, doc.save)


def get_batch_from_bundle(bundle):
	from erpnext.stock.serial_batch_bundle import get_batch_nos

	batches = get_batch_nos(bundle)

	return list(batches.keys())[0]


def get_serial_nos_from_bundle(bundle):
	from erpnext.stock.serial_batch_bundle import get_serial_nos

	serial_nos = get_serial_nos(bundle)
	return sorted(serial_nos) if serial_nos else []


def make_serial_batch_bundle(kwargs):
	from erpnext.stock.serial_batch_bundle import SerialBatchCreation

	if isinstance(kwargs, dict):
		kwargs = frappe._dict(kwargs)

	type_of_transaction = "Inward" if kwargs.qty > 0 else "Outward"
	if kwargs.get("type_of_transaction"):
		type_of_transaction = kwargs.get("type_of_transaction")

	sb = SerialBatchCreation(
		{
			"item_code": kwargs.item_code,
			"warehouse": kwargs.warehouse,
			"voucher_type": kwargs.voucher_type,
			"voucher_no": kwargs.voucher_no,
			"posting_date": kwargs.posting_date,
			"posting_time": kwargs.posting_time,
			"qty": kwargs.qty,
			"avg_rate": kwargs.rate,
			"batches": kwargs.batches,
			"serial_nos": kwargs.serial_nos,
			"type_of_transaction": type_of_transaction,
			"company": kwargs.company or "_Test Company",
			"do_not_submit": kwargs.do_not_submit,
		}
	)

	if not kwargs.get("do_not_save"):
		return sb.make_serial_and_batch_bundle()

	return sb
