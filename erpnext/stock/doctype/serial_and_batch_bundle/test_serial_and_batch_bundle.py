# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import json
from unittest.mock import patch

import frappe
from frappe.utils import add_days, add_to_date, flt, nowtime, today

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.serial_and_batch_bundle.inline_editor import resolve_csv_entries
from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
	add_serial_batch_ledgers,
	combine_datetime,
	get_available_batches_qty,
	get_qty_based_available_batches,
	get_type_of_transaction,
	parse_serial_nos,
)
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.tests.utils import ERPNextTestSuite


class TestSerialBatchBundleEntry(ERPNextTestSuite):
	def make_bundle(self, has_batch_no=0):
		item = make_item(properties={"is_stock_item": 1, "has_serial_no": 1, "has_batch_no": has_batch_no})
		return frappe.get_doc(
			doctype="Serial and Batch Bundle",
			item_code=item.name,
			has_serial_no=1,
			has_batch_no=has_batch_no,
			company="_Test Company",
			warehouse="_Test Warehouse - _TC",
			voucher_type="Purchase Receipt",
			type_of_transaction="Inward",
			posting_datetime=combine_datetime(today(), nowtime()),
		)

	def test_manual_serials_resolve_by_item_and_save(self):
		bundles = [self.make_bundle(), self.make_bundle()]
		for bundle in bundles:
			name = bundle.add_serial_batch({"serial_nos": "Form-Serial"})
			self.assertEqual(name, bundle.name)
			bundle.reload()
			serial = frappe.get_doc("Serial No", bundle.entries[0].serial_no)
			self.assertEqual((serial.item_code, serial.serial_no), (bundle.item_code, "Form-Serial"))
			self.assertEqual(serial.company, bundle.company)
		self.assertNotEqual(bundles[0].entries[0].serial_no, bundles[1].entries[0].serial_no)
		name = bundles[0].name
		self.assertEqual(bundles[0].add_serial_batch({"serial_nos": "Replacement-Serial"}), name)
		bundles[0].reload()
		self.assertEqual(len(bundles[0].entries), 1)
		self.assertEqual(
			frappe.db.get_value("Serial No", bundles[0].entries[0].serial_no, "serial_no"),
			"Replacement-Serial",
		)

	def test_csv_pairs_are_saved_together(self):
		bundle = self.make_bundle(has_batch_no=1)
		serials = [{"serial_no": "Form-Serial", "batch_no": "Form-Batch", "qty": 1}]
		batches = [{"batch_no": "Form-Batch", "qty": 1}]
		with patch(
			"erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle.read_serial_batch_csv",
			return_value=(serials, batches),
		):
			bundle.add_serial_batch({"csv_file": "/private/files/serials.csv"})
		bundle.reload()
		self.assertEqual(len(bundle.entries), 1)
		entry = bundle.entries[0]
		serial = frappe.get_doc("Serial No", entry.serial_no)
		batch = frappe.get_doc("Batch", entry.batch_no)
		self.assertEqual((serial.serial_no, batch.batch_id), ("Form-Serial", "Form-Batch"))
		self.assertEqual(serial.batch_no, batch.name)
		self.assertEqual(bundle.total_qty, 1)

	def test_outward_bundle_cannot_create_serials(self):
		bundle = self.make_bundle()
		bundle.type_of_transaction = "Outward"
		with self.assertRaisesRegex(frappe.ValidationError, "does not exist for Item"):
			bundle.add_serial_batch({"serial_nos": "Missing-Serial"})
		self.assertFalse(
			frappe.db.exists("Serial No", {"item_code": bundle.item_code, "serial_no": "Missing-Serial"})
		)

	def test_submitted_bundle_rejects_number_entry(self):
		bundle = self.make_bundle()
		bundle.docstatus = 1
		with self.assertRaisesRegex(frappe.ValidationError, "draft bundle"):
			bundle.add_serial_batch({"serial_nos": "Missing-Serial"})
		self.assertFalse(
			frappe.db.exists("Serial No", {"item_code": bundle.item_code, "serial_no": "Missing-Serial"})
		)

	def test_number_entry_follows_the_bundle_not_the_serial_master(self):
		bundle = self.make_bundle()
		user = frappe.get_doc(
			doctype="User",
			email="bundle-entry-stock-user@example.com",
			first_name="Bundle Entry",
			send_welcome_email=0,
			roles=[{"role": "Stock User"}],
		).insert()
		with self.set_user(user.name):
			self.assertFalse(frappe.has_permission("Serial No", "create"))
			bundle.add_serial_batch({"serial_nos": "Missing-Serial"})
		self.assertTrue(
			frappe.db.exists("Serial No", {"item_code": bundle.item_code, "serial_no": "Missing-Serial"})
		)


class TestSerialandBatchBundle(ERPNextTestSuite):
	def test_naming_for_sabb(self):
		frappe.db.set_single_value(
			"Stock Settings", "set_serial_and_batch_bundle_naming_based_on_naming_series", 1
		)

		serial_item_code = "New Serial No Valuation 11"
		make_item(
			serial_item_code,
			{
				"has_serial_no": 1,
				"serial_no_series": "TEST-A-SER-VAL-.#####",
				"is_stock_item": 1,
			},
		)

		serial_ids = []
		for sn in ["TEST-A-SER-VAL-00001", "TEST-A-SER-VAL-00002"]:
			if not frappe.db.exists("Serial No", {"item_code": serial_item_code, "serial_no": sn}):
				frappe.get_doc(
					{
						"doctype": "Serial No",
						"serial_no": sn,
						"item_code": serial_item_code,
						"company": "_Test Company",
					}
				).insert(ignore_permissions=True)
			serial_ids.append(
				frappe.db.get_value("Serial No", {"item_code": serial_item_code, "serial_no": sn}, "name")
			)

		bundle_doc = make_serial_batch_bundle(
			{
				"item_code": serial_item_code,
				"warehouse": "_Test Warehouse - _TC",
				"voucher_type": "Stock Entry",
				"posting_date": today(),
				"posting_time": nowtime(),
				"qty": 10,
				"serial_nos": serial_ids,
				"type_of_transaction": "Inward",
				"do_not_submit": True,
			}
		)

		self.assertTrue(bundle_doc.name.startswith("SABB-"))

		frappe.db.set_single_value(
			"Stock Settings", "set_serial_and_batch_bundle_naming_based_on_naming_series", 0
		)

		bundle_doc = make_serial_batch_bundle(
			{
				"item_code": serial_item_code,
				"warehouse": "_Test Warehouse - _TC",
				"voucher_type": "Stock Entry",
				"posting_date": today(),
				"posting_time": nowtime(),
				"qty": 10,
				"serial_nos": serial_ids,
				"type_of_transaction": "Inward",
				"do_not_submit": True,
			}
		)

		self.assertFalse(bundle_doc.name.startswith("SABB-"))

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

	def test_outward_batch_valuation_takes_transaction_advisory_lock(self):
		if frappe.db.db_type != "postgres":
			self.skipTest("advisory locks are a PostgreSQL feature")

		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		item_code = make_item(
			properties={
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "TEST-ADV-LCK-.#####",
				"is_stock_item": 1,
			},
		).name

		make_purchase_receipt(item_code=item_code, warehouse="_Test Warehouse - _TC", qty=5, rate=100)

		def held_advisory_locks():
			return frappe.db.sql(
				"SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' AND pid = pg_backend_pid()"
			)[0][0]

		before = held_advisory_locks()
		create_delivery_note(item_code=item_code, warehouse="_Test Warehouse - _TC", qty=2, rate=200)
		self.assertGreater(held_advisory_locks(), before)

	def test_old_batch_valuation(self):
		with patch.dict(
			frappe.flags, {"ignore_serial_batch_bundle_validation": True, "use_serial_and_batch_fields": True}
		):
			batch_item_code = "Old Batch Item Valuation 1"
			make_item(
				batch_item_code,
				{
					"has_batch_no": 1,
					"batch_number_series": "TEST-OLD-BAT-VAL-.#####",
					"create_new_batch": 1,
					"is_stock_item": 1,
					"valuation_method": "FIFO",
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
				).insert(ignore_permissions=True, set_name=batch_id)

				self.assertTrue(batch_doc.use_batchwise_valuation)
				batch_doc.db_set(
					{
						"use_batchwise_valuation": 0,
						"batch_qty": 30,
					}
				)

			stock_queue = []
			qty_after_transaction = 0
			balance_value = 0
			for qty, valuation in {10: 100, 20: 200}.items():
				stock_queue.append([qty, valuation])
				qty_after_transaction += qty
				balance_value += qty * valuation

				doc = frappe.get_doc(
					{
						"doctype": "Stock Ledger Entry",
						"posting_date": today(),
						"posting_time": nowtime(),
						"batch_no": batch_id,
						"incoming_rate": valuation,
						"qty_after_transaction": qty_after_transaction,
						"stock_value_difference": valuation * qty,
						"stock_value": balance_value,
						"balance_value": balance_value,
						"valuation_rate": balance_value / qty_after_transaction,
						"actual_qty": qty,
						"item_code": batch_item_code,
						"warehouse": "_Test Warehouse - _TC",
						"stock_queue": json.dumps(stock_queue),
						"company": "_Test Company",
					}
				)

				doc.set_posting_datetime()
				doc.flags.ignore_permissions = True
				doc.flags.ignore_mandatory = True
				doc.flags.ignore_links = True
				doc.flags.ignore_validate = True
				doc.submit()
				doc.reload()

		se = make_stock_entry(
			item_code=batch_item_code,
			source="_Test Warehouse - _TC",
			qty=10,
			use_serial_batch_fields=True,
			batch_no=batch_id,
		)

		sle = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": batch_item_code, "is_cancelled": 0, "voucher_no": se.name},
			["stock_value_difference", "stock_queue"],
			as_dict=True,
		)

		self.assertEqual(flt(sle.stock_value_difference), 1000.00 * -1)
		self.assertEqual(json.loads(sle.stock_queue), [[20, 200]])

		se = make_stock_entry(
			item_code=batch_item_code,
			target="_Test Warehouse - _TC",
			qty=10,
			rate=100,
			batch_no=batch_id,
			use_serial_batch_fields=True,
		)

		sle = frappe.db.get_value(
			"Serial and Batch Entry",
			{"parent": se.items[0].serial_and_batch_bundle, "docstatus": 1},
			["stock_value_difference", "stock_queue"],
			as_dict=True,
		)

		self.assertEqual(flt(sle.stock_value_difference), 1000.00)
		self.assertEqual(json.loads(sle.stock_queue), [[20, 200], [10, 100]])

		se = make_stock_entry(
			item_code=batch_item_code,
			target="_Test Warehouse - _TC",
			qty=10,
			rate=100,
			use_serial_batch_fields=True,
		)

		sle = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": batch_item_code, "is_cancelled": 0, "voucher_no": se.name},
			["stock_value_difference", "stock_queue"],
			as_dict=True,
		)

		self.assertEqual(flt(sle.stock_value_difference), 1000.00)
		self.assertEqual(json.loads(sle.stock_queue), [[20, 200], [10, 100]])

		se = make_stock_entry(
			item_code=batch_item_code,
			source="_Test Warehouse - _TC",
			qty=30,
			use_serial_batch_fields=False,
		)

		sle = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": batch_item_code, "is_cancelled": 0, "voucher_no": se.name},
			["stock_value_difference", "stock_queue", "stock_value"],
			as_dict=True,
		)

		self.assertEqual(flt(sle.stock_value_difference), 5000.00 * -1)
		self.assertFalse(json.loads(sle.stock_queue or "[]"))
		self.assertEqual(flt(sle.stock_value), 1000.0)

		se = make_stock_entry(
			item_code=batch_item_code,
			source="_Test Warehouse - _TC",
			qty=10,
			use_serial_batch_fields=False,
		)

		sle = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": batch_item_code, "is_cancelled": 0, "voucher_no": se.name},
			["stock_value_difference", "stock_queue", "stock_value"],
			as_dict=True,
		)

		self.assertEqual(flt(sle.stock_value_difference), 1000.00 * -1)
		self.assertFalse(json.loads(sle.stock_queue or "[]"))
		self.assertEqual(flt(sle.stock_value), 0.0)

	def test_old_moving_avg_item_with_without_batchwise_valuation(self):
		with patch.dict(
			frappe.flags, {"ignore_serial_batch_bundle_validation": True, "use_serial_and_batch_fields": True}
		):
			batch_item_code = "Old Batch Item Valuation 2"
			make_item(
				batch_item_code,
				{
					"has_batch_no": 1,
					"batch_number_series": "TEST-OLD2-BAT-VAL-.#####",
					"create_new_batch": 1,
					"is_stock_item": 1,
					"valuation_method": "Moving Average",
				},
			)

			non_batchwise_val_batches = [
				"TEST-OLD2-BAT-VAL-00001",
				"TEST-OLD2-BAT-VAL-00002",
				"TEST-OLD2-BAT-VAL-00003",
				"TEST-OLD2-BAT-VAL-00004",
			]

			for batch_id in non_batchwise_val_batches:
				if not frappe.db.exists("Batch", batch_id):
					batch_doc = frappe.get_doc(
						{
							"doctype": "Batch",
							"batch_id": batch_id,
							"item": batch_item_code,
							"use_batchwise_valuation": 0,
						}
					).insert(ignore_permissions=True, set_name=batch_id)

					self.assertTrue(batch_doc.use_batchwise_valuation)
					batch_doc.db_set(
						{
							"use_batchwise_valuation": 0,
							"batch_qty": 20,
						}
					)

			qty_after_transaction = 0
			balance_value = 0
			i = 0
			for batch_id in non_batchwise_val_batches:
				i += 1
				qty = 20
				valuation = 100 * i
				qty_after_transaction += qty
				balance_value += qty * valuation

				doc = frappe.get_doc(
					{
						"doctype": "Stock Ledger Entry",
						"posting_date": today(),
						"posting_time": nowtime(),
						"batch_no": batch_id,
						"incoming_rate": valuation,
						"qty_after_transaction": qty_after_transaction,
						"stock_value_difference": valuation * qty,
						"stock_value": balance_value,
						"balance_value": balance_value,
						"valuation_rate": balance_value / qty_after_transaction,
						"actual_qty": qty,
						"item_code": batch_item_code,
						"warehouse": "_Test Warehouse - _TC",
						"company": "_Test Company",
					}
				)

				doc.set_posting_datetime()
				doc.flags.ignore_permissions = True
				doc.flags.ignore_mandatory = True
				doc.flags.ignore_links = True
				doc.flags.ignore_validate = True
				doc.submit()
				doc.reload()

		se = make_stock_entry(
			item_code=batch_item_code,
			target="_Test Warehouse - _TC",
			qty=30,
			rate=355,
			use_serial_batch_fields=True,
		)

		se = make_stock_entry(
			item_code=batch_item_code,
			source="_Test Warehouse - _TC",
			qty=70,
			use_serial_batch_fields=True,
		)

		sle = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": batch_item_code, "is_cancelled": 0, "voucher_no": se.name},
			["qty_after_transaction", "stock_value"],
			as_dict=True,
		)

		self.assertEqual(flt(sle.stock_value), 14000.0)
		self.assertEqual(flt(sle.qty_after_transaction), 40.0)

		se = make_stock_entry(
			item_code=batch_item_code,
			target="_Test Warehouse - _TC",
			qty=10,
			rate=200,
			use_serial_batch_fields=True,
		)

		se = make_stock_entry(
			item_code=batch_item_code,
			source="_Test Warehouse - _TC",
			qty=50,
			use_serial_batch_fields=True,
		)

		sle = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": batch_item_code, "is_cancelled": 0, "voucher_no": se.name},
			["qty_after_transaction", "stock_value"],
			as_dict=True,
		)

		self.assertEqual(flt(sle.stock_value), 0.0)
		self.assertEqual(flt(sle.qty_after_transaction), 0.0)

	def test_moving_avg_item_with_mixed_batchwise_valuation(self):
		"""A Moving Average item holding both batchwise and non batchwise batches.

		The non batchwise batches were consumed at the pooled warehouse rate before batch
		level valuation existed, so the sum of their stock value differences no longer
		tracks the sum of their quantities. Valuing a later outward off that drained pool
		used to hand back a negative rate, which the callers read as abs() and used to
		overdraw the warehouse, driving stock value negative.
		"""
		frappe.db.set_single_value("Stock Settings", "do_not_use_batchwise_valuation", 0)

		item_code = "Old Batch Item Mixed Valuation 1"
		make_item(
			item_code,
			{
				"has_batch_no": 1,
				"batch_number_series": "TEST-MIX-BAT-VAL-.#####",
				"create_new_batch": 1,
				"is_stock_item": 1,
				"valuation_method": "Moving Average",
			},
		)

		warehouse = "_Test Warehouse - _TC"
		non_batchwise_batch = "TEST-MIX-BAT-VAL-00001"
		batchwise_batch = "TEST-MIX-BAT-VAL-00002"

		for batch_id, use_batchwise_valuation in (
			(non_batchwise_batch, 0),
			(batchwise_batch, 1),
		):
			if not frappe.db.exists("Batch", batch_id):
				batch_doc = frappe.get_doc(
					{
						"doctype": "Batch",
						"batch_id": batch_id,
						"item": item_code,
						"use_batchwise_valuation": use_batchwise_valuation,
					}
				).insert(ignore_permissions=True, set_name=batch_id)

				batch_doc.db_set("use_batchwise_valuation", use_batchwise_valuation)

		# ERPNextTestSuite.tearDown only rolls the db back, it does not restore
		# frappe.local.flags, so these have to be put back even if a submit raises
		previous_flags = (
			frappe.flags.ignore_serial_batch_bundle_validation,
			frappe.flags.use_serial_and_batch_fields,
		)
		frappe.flags.ignore_serial_batch_bundle_validation = True
		frappe.flags.use_serial_and_batch_fields = True

		# Legacy ledger, written the way the pre batch-level-valuation code posted it:
		#   in  20 @ 50  of the non batchwise batch  -> warehouse 20 qty / 1000
		#   in  20 @ 450 of the batchwise batch      -> warehouse 40 qty / 10000, rate 250
		#   out 20       of the non batchwise batch, priced at the pooled rate of 250
		# which leaves the non batchwise batch with a pool of -4000 value against 0 qty.
		legacy_entries = [
			(non_batchwise_batch, 20, 1000, 20, 1000),
			(batchwise_batch, 20, 9000, 40, 10000),
			(non_batchwise_batch, -20, -5000, 20, 5000),
		]

		try:
			for batch_id, qty, svd, qty_after_transaction, stock_value in legacy_entries:
				doc = frappe.get_doc(
					{
						"doctype": "Stock Ledger Entry",
						"posting_date": today(),
						"posting_time": nowtime(),
						"batch_no": batch_id,
						"incoming_rate": (svd / qty) if qty > 0 else 0,
						"qty_after_transaction": qty_after_transaction,
						"stock_value_difference": svd,
						"stock_value": stock_value,
						"balance_value": stock_value,
						"valuation_rate": stock_value / qty_after_transaction,
						"actual_qty": qty,
						"item_code": item_code,
						"warehouse": warehouse,
					}
				)

				doc.set_posting_datetime()
				doc.flags.ignore_permissions = True
				doc.flags.ignore_mandatory = True
				doc.flags.ignore_links = True
				doc.flags.ignore_validate = True
				doc.submit()
		finally:
			(
				frappe.flags.ignore_serial_batch_bundle_validation,
				frappe.flags.use_serial_and_batch_fields,
			) = previous_flags

		# Refill the drained non batchwise batch, then consume it back out.
		make_stock_entry(
			item_code=item_code,
			target=warehouse,
			qty=10,
			rate=50,
			batch_no=non_batchwise_batch,
			use_serial_batch_fields=True,
		)

		se = make_stock_entry(
			item_code=item_code,
			source=warehouse,
			qty=10,
			batch_no=non_batchwise_batch,
			use_serial_batch_fields=True,
		)

		sle = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": item_code, "is_cancelled": 0, "voucher_no": se.name},
			["qty_after_transaction", "stock_value", "stock_value_difference"],
			as_dict=True,
		)

		self.assertEqual(flt(sle.qty_after_transaction), 20.0)

		# The non batchwise batch is left holding a pool of -3500 against 10 qty, so its
		# own rate works out to -350. That used to be taken as abs() = 350 and the 10 units
		# drew 3500 out of the warehouse, against the 50 each they were actually bought at.
		# The drained pool is rejected now and the warehouse rate of 5500 / 30 is used.
		self.assertEqual(flt(sle.stock_value_difference, 2), -1833.33)
		self.assertEqual(flt(sle.stock_value, 2), 3666.67)
		self.assertGreaterEqual(flt(sle.stock_value), 0.0)

		# a batch is never valued at a negative rate, and the rate stored on the ledger
		# entry stays in step with the sign every reader applies to it
		bundle = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": item_code, "is_cancelled": 0, "voucher_no": se.name},
			"serial_and_batch_bundle",
		)

		incoming_rate = frappe.db.get_value(
			"Serial and Batch Entry",
			{"parent": bundle, "batch_no": non_batchwise_batch},
			"incoming_rate",
		)

		self.assertGreaterEqual(flt(incoming_rate), 0.0)
		self.assertEqual(flt(incoming_rate, 2), 183.33)

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

		with patch.dict(
			frappe.flags, {"ignore_serial_batch_bundle_validation": True, "use_serial_and_batch_fields": True}
		):
			serial_no_id = "Old Serial No 1"
			if not frappe.db.exists("Serial No", serial_no_id):
				sn_doc = frappe.get_doc(
					{
						"doctype": "Serial No",
						"serial_no": serial_no_id,
						"item_code": serial_no_item_code,
						"company": "_Test Company",
					}
				).insert(ignore_permissions=True, set_name=serial_no_id)

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

	def test_auto_delete_draft_serial_and_batch_bundle(self):
		serial_and_batch_code = "New Serial No Auto Delete 1"
		make_item(
			serial_and_batch_code,
			{
				"has_serial_no": 1,
				"serial_no_series": "TEST-SER-VALL-.#####",
				"is_stock_item": 1,
			},
		)

		ste = make_stock_entry(
			item_code=serial_and_batch_code,
			target="_Test Warehouse - _TC",
			qty=1,
			rate=500,
			do_not_submit=True,
		)

		serial_no = "SN-TEST-AUTO-DEL"
		if not frappe.db.exists("Serial No", {"item_code": serial_and_batch_code, "serial_no": serial_no}):
			frappe.get_doc(
				{
					"doctype": "Serial No",
					"serial_no": serial_no,
					"item_code": serial_and_batch_code,
					"company": "_Test Company",
				}
			).insert(ignore_permissions=True)
		serial_no = frappe.db.get_value(
			"Serial No", {"item_code": serial_and_batch_code, "serial_no": serial_no}, "name"
		)

		bundle_doc = make_serial_batch_bundle(
			{
				"item_code": serial_and_batch_code,
				"warehouse": "_Test Warehouse - _TC",
				"voucher_type": "Stock Entry",
				"posting_date": ste.posting_date,
				"posting_time": ste.posting_time,
				"qty": 1,
				"serial_nos": [serial_no],
				"type_of_transaction": "Inward",
				"do_not_submit": True,
			}
		)

		bundle_doc.reload()
		ste.items[0].serial_and_batch_bundle = bundle_doc.name
		ste.save()
		ste.reload()

		ste.delete()
		self.assertFalse(frappe.db.exists("Serial and Batch Bundle", bundle_doc.name))

	def test_serial_and_batch_bundle_company(self):
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
		from erpnext.stock.services.serial_batch_bundle_service import SerialBatchBundleService

		item = make_item(
			"Test Serial and Batch Bundle Company Item",
			properties={
				"has_serial_no": 1,
				"serial_no_series": "TT-SER-VAL-.#####",
			},
		).name

		pr = make_purchase_receipt(
			item_code=item,
			warehouse="_Test Warehouse - _TC",
			qty=3,
			rate=500,
			do_not_submit=True,
		)

		entries = []
		for serial_no in ["TT-SER-VAL-00001", "TT-SER-VAL-00002", "TT-SER-VAL-00003"]:
			if not frappe.db.exists("Serial No", {"item_code": item, "serial_no": serial_no}):
				frappe.get_doc(
					{
						"doctype": "Serial No",
						"serial_no": serial_no,
						"item_code": item,
						"company": "_Test Company",
					}
				).insert(ignore_permissions=True)
			serial_id = frappe.db.get_value("Serial No", {"item_code": item, "serial_no": serial_no}, "name")
			entries.append(frappe._dict({"serial_no": serial_id, "qty": 1}))

		item_row = pr.items[0]
		item_row.type_of_transaction = "Inward"
		item_row.is_rejected = 0
		sn_doc = add_serial_batch_ledgers(entries, item_row, pr, "_Test Warehouse - _TC")
		self.assertEqual(sn_doc.company, "_Test Company")

		pr.company = "_Test Company 1"
		for fieldname in ("serial_and_batch_bundle", "rejected_serial_and_batch_bundle"):
			item_row.serial_and_batch_bundle = None
			item_row.rejected_serial_and_batch_bundle = None
			item_row.set(fieldname, sn_doc.name)

			with self.subTest(fieldname=fieldname):
				with self.assertRaisesRegex(
					frappe.ValidationError,
					"Company _Test Company 1 does not match with the company _Test Company",
				):
					SerialBatchBundleService(pr).validate_warehouse_of_sabb()

	def test_auto_cancel_serial_and_batch(self):
		item_code = make_item(
			properties={"has_serial_no": 1, "serial_no_series": "ATC-TT-SER-VAL-.#####"}
		).name

		se = make_stock_entry(
			item_code=item_code,
			target="_Test Warehouse - _TC",
			qty=5,
			rate=500,
		)

		bundle = se.items[0].serial_and_batch_bundle
		docstatus = frappe.db.get_value("Serial and Batch Bundle", bundle, "docstatus")
		self.assertEqual(docstatus, 1)

		se.cancel()
		docstatus = frappe.db.get_value("Serial and Batch Bundle", bundle, "docstatus")
		self.assertEqual(docstatus, 2)

	def test_submitted_bundle_entries_cannot_be_mutated(self):
		# A submitted Serial and Batch Bundle is the immutable source of truth for the stock
		# ledger, live batch availability and repost/valuation replay. update_serial_batch_no_ledgers
		# (which the whitelisted add_serial_batch_ledgers delegates to for an existing bundle) must
		# refuse to rebuild -- and thereby inflate -- the quantities of an already submitted bundle.
		from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
			update_serial_batch_no_ledgers,
		)

		item_code = make_item(
			properties={
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "TAMPER-SBB-.#####",
			}
		).name

		se = make_stock_entry(
			item_code=item_code,
			target="_Test Warehouse - _TC",
			qty=10,
			rate=100,
		)

		bundle = se.items[0].serial_and_batch_bundle
		self.assertEqual(frappe.db.get_value("Serial and Batch Bundle", bundle, "docstatus"), 1)

		original = frappe.db.get_value(
			"Serial and Batch Entry", {"parent": bundle}, ["name", "batch_no", "qty"], as_dict=True
		)
		self.assertEqual(original.qty, 10)

		# Attempt to forge the submitted bundle: keep the same batch but inflate qty. The guard
		# fires immediately after the bundle is loaded (docstatus check), so child_row / parent_doc
		# only need the minimal fields the function reads.
		tampered_entries = [{"batch_no": original.batch_no, "qty": 1000}]
		child_row = frappe._dict({"name": se.items[0].name})
		parent_doc = frappe._dict({"posting_date": today(), "posting_time": nowtime()})

		self.assertRaises(
			frappe.ValidationError,
			update_serial_batch_no_ledgers,
			bundle,
			tampered_entries,
			child_row,
			parent_doc,
		)

		# The on-disk quantity must be untouched by the rejected mutation attempt.
		self.assertEqual(
			frappe.db.get_value("Serial and Batch Entry", original.name, "qty"),
			10,
		)

	@ERPNextTestSuite.change_settings("Stock Settings", {"do_not_use_batchwise_valuation": 0})
	def test_csv_batch_reuses_existing_record(self):
		item_code = make_item(properties={"has_batch_no": 1}).name
		batch_id = "TEST-BATTCCH-VAL-00001"
		entries = resolve_csv_entries(
			[{"batch_no": batch_id, "qty": 1}], item_code, "Inward", "_Test Company"
		)
		batch = frappe.get_doc("Batch", entries[0].batch_no)
		self.assertEqual((batch.item, batch.batch_id), (item_code, batch_id))
		self.assertNotEqual(batch.name, batch_id)
		self.assertEqual(batch.use_batchwise_valuation, 1)

		entries = resolve_csv_entries(
			[{"batch_no": batch_id.lower(), "qty": 2}], item_code, "Inward", "_Test Company"
		)
		self.assertEqual(entries, [{"serial_no": None, "batch_no": batch.name, "qty": 2}])
		self.assertEqual(frappe.db.count("Batch", {"item": item_code, "batch_id": batch_id}), 1)

	def test_serial_number_reuses_existing_record(self):
		item_code = make_item(properties={"has_serial_no": 1}).name
		serial_no = "TEST-SNID-VAL-00001"
		entries = resolve_csv_entries(
			[{"serial_no": serial_no, "qty": 1}], item_code, "Inward", "_Test Company"
		)
		serial = frappe.get_doc("Serial No", entries[0].serial_no)
		self.assertEqual((serial.item_code, serial.serial_no), (item_code, serial_no))
		self.assertNotEqual(serial.name, serial_no)
		self.assertEqual((serial.company, serial.status), ("_Test Company", "Inactive"))

		entries = resolve_csv_entries(
			[{"serial_no": serial_no.lower(), "qty": 1}], item_code, "Inward", "_Test Company"
		)
		self.assertEqual(entries, [{"serial_no": serial.name, "batch_no": None, "qty": 1}])
		self.assertEqual(frappe.db.count("Serial No", {"item_code": item_code, "serial_no": serial_no}), 1)

	@ERPNextTestSuite.change_settings(
		"Stock Settings", {"auto_create_serial_and_batch_bundle_for_outward": 1}
	)
	def test_duplicate_serial_and_batch_bundle(self):
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		item_code = make_item(properties={"is_stock_item": 1, "has_serial_no": 1}).name

		serial = frappe.get_doc(
			doctype="Serial No", item_code=item_code, serial_no=f"{item_code}-001", company="_Test Company"
		).insert()

		pr1 = make_purchase_receipt(item=item_code, qty=1, rate=500, serial_no=[serial.name])
		pr2 = make_purchase_receipt(item=item_code, qty=1, rate=500, do_not_save=True)

		pr1.reload()
		pr2.items[0].serial_and_batch_bundle = pr1.items[0].serial_and_batch_bundle

		self.assertRaises(frappe.exceptions.ValidationError, pr2.save)

	def test_serial_no_valuation_for_legacy_ledgers(self):
		sn_item = make_item(
			"Test Serial No Valuation for Legacy Ledgers",
			properties={"has_serial_no": 1, "serial_no_series": "SNN-TSNVL-.#####"},
		).name

		serial_nos = []
		for serial_no in [f"{sn_item}-0001", f"{sn_item}-0002"]:
			if not frappe.db.exists("Serial No", serial_no):
				sn_doc = frappe.get_doc(
					{
						"doctype": "Serial No",
						"serial_no": serial_no,
						"item_code": sn_item,
						"company": "_Test Company",
					}
				).insert(ignore_permissions=True, set_name=serial_no)
				serial_nos.append(serial_no)

		with patch.dict(frappe.flags, {"ignore_serial_batch_bundle_validation": True}):
			qty_after_transaction = 0.0
			stock_value = 0.0
			for row in [{"qty": 2, "rate": 100}, {"qty": -2, "rate": 100}, {"qty": 2, "rate": 200}]:
				row = frappe._dict(row)
				qty_after_transaction += row.qty
				stock_value += row.rate * row.qty

				doc = frappe.get_doc(
					{
						"doctype": "Stock Ledger Entry",
						"posting_date": today(),
						"posting_time": nowtime(),
						"incoming_rate": row.rate if row.qty > 0 else 0,
						"qty_after_transaction": qty_after_transaction,
						"stock_value_difference": row.rate * row.qty,
						"stock_value": stock_value,
						"valuation_rate": row.rate,
						"actual_qty": row.qty,
						"item_code": sn_item,
						"warehouse": "_Test Warehouse - _TC",
						"serial_no": "\n".join(serial_nos),
						"company": "_Test Company",
					}
				)
				doc.set_posting_datetime()
				doc.flags.ignore_permissions = True
				doc.flags.ignore_mandatory = True
				doc.flags.ignore_links = True
				doc.flags.ignore_validate = True
				doc.submit()

				for sn in serial_nos:
					sn_doc = frappe.get_doc("Serial No", sn)
					if row.qty > 0:
						sn_doc.db_set("warehouse", "_Test Warehouse - _TC")
					else:
						sn_doc.db_set("warehouse", "")

		se = make_stock_entry(
			item_code=sn_item,
			qty=2,
			source="_Test Warehouse - _TC",
			serial_no="\n".join(serial_nos),
			use_serial_batch_fields=True,
			do_not_submit=True,
		)

		se.save()
		se.submit()

		stock_value_difference = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_no": se.name, "is_cancelled": 0, "voucher_type": "Stock Entry"},
			"stock_value_difference",
		)

		self.assertEqual(flt(stock_value_difference, 2), 400.0 * -1)

		se = make_stock_entry(
			item_code=sn_item,
			qty=1,
			rate=353,
			target="_Test Warehouse - _TC",
		)

		serial_no = get_serial_numbers_from_bundle(se.items[0].serial_and_batch_bundle)[0]

		se = make_stock_entry(
			item_code=sn_item,
			qty=1,
			source="_Test Warehouse - _TC",
			serial_no=serial_no,
			use_serial_batch_fields=True,
		)

		stock_value_difference = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_no": se.name, "is_cancelled": 0, "voucher_type": "Stock Entry"},
			"stock_value_difference",
		)

		self.assertEqual(flt(stock_value_difference, 2), 353.0 * -1)

	def test_pick_serial_nos_for_batch_item(self):
		item_code = make_item(
			"Test Pick Serial Nos for Batch Item 1",
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "PSNBI-TSNVL-.#####",
				"has_serial_no": 1,
				"serial_no_series": "SN-PSNBI-TSNVL-.#####",
			},
		).name

		se = make_stock_entry(
			item_code=item_code,
			qty=10,
			target="_Test Warehouse - _TC",
			rate=500,
		)

		batch1 = get_batch_from_bundle(se.items[0].serial_and_batch_bundle)
		serial_nos1 = get_serial_nos_from_bundle(se.items[0].serial_and_batch_bundle)

		se = make_stock_entry(
			item_code=item_code,
			qty=10,
			target="_Test Warehouse - _TC",
			rate=500,
		)

		batch2 = get_batch_from_bundle(se.items[0].serial_and_batch_bundle)
		serial_nos2 = get_serial_nos_from_bundle(se.items[0].serial_and_batch_bundle)

		se = make_stock_entry(
			item_code=item_code,
			qty=10,
			source="_Test Warehouse - _TC",
			use_serial_batch_fields=True,
			batch_no=batch2,
		)

		serial_nos = get_serial_nos_from_bundle(se.items[0].serial_and_batch_bundle)
		self.assertEqual(serial_nos, serial_nos2)

		se = make_stock_entry(
			item_code=item_code,
			qty=10,
			source="_Test Warehouse - _TC",
			use_serial_batch_fields=True,
			batch_no=batch1,
		)

		serial_nos = get_serial_nos_from_bundle(se.items[0].serial_and_batch_bundle)
		self.assertEqual(serial_nos, serial_nos1)

	def test_auto_create_serial_and_batch_bundle_for_outward_for_batch_item(self):
		item_code = make_item(
			"Test Auto Create Batch Bundle for Outward 1",
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"batch_number_series": "ACSBBO-TACSB-.#####",
			},
		).name

		if not frappe.db.exists("Batch", {"item": item_code, "batch_id": "ACSBBO-TACSB-00001"}):
			frappe.get_doc(
				{
					"doctype": "Batch",
					"batch_id": "ACSBBO-TACSB-00001",
					"item": item_code,
					"company": "_Test Company",
				}
			).insert(ignore_permissions=True)
		batch_no = frappe.db.get_value("Batch", {"item": item_code, "batch_id": "ACSBBO-TACSB-00001"}, "name")

		make_stock_entry(
			item_code=item_code,
			qty=10,
			target="_Test Warehouse - _TC",
			rate=500,
			use_serial_batch_fields=True,
			batch_no=batch_no,
		)

		dispatch = make_stock_entry(
			item_code=item_code,
			qty=10,
			target="_Test Warehouse - _TC",
			rate=500,
			do_not_submit=True,
		)

		original_value = frappe.db.get_single_value(
			"Stock Settings", "auto_create_serial_and_batch_bundle_for_outward"
		)

		frappe.db.set_single_value("Stock Settings", "auto_create_serial_and_batch_bundle_for_outward", 0)
		self.assertRaises(frappe.ValidationError, dispatch.submit)

		frappe.db.set_single_value("Stock Settings", "auto_create_serial_and_batch_bundle_for_outward", 1)
		dispatch.submit()

		frappe.db.set_single_value(
			"Stock Settings", "auto_create_serial_and_batch_bundle_for_outward", original_value
		)

	def test_voucher_detail_no(self):
		item_code = make_item(
			"Test Voucher Detail No 1",
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "TST-VDN-.#####",
			},
		).name

		se = make_stock_entry(
			item_code=item_code,
			qty=10,
			target="_Test Warehouse - _TC",
			rate=500,
			use_serial_batch_fields=True,
			do_not_submit=True,
		)

		if not frappe.db.exists("Batch", {"item": item_code, "batch_id": "TST-ACSBBO-TACSB-00001"}):
			frappe.get_doc(
				{
					"doctype": "Batch",
					"batch_id": "TST-ACSBBO-TACSB-00001",
					"item": item_code,
					"company": "_Test Company",
				}
			).insert(ignore_permissions=True)
		batch_no = frappe.db.get_value(
			"Batch", {"item": item_code, "batch_id": "TST-ACSBBO-TACSB-00001"}, "name"
		)

		bundle_doc = make_serial_batch_bundle(
			{
				"item_code": item_code,
				"warehouse": "_Test Warehouse - _TC",
				"voucher_type": "Stock Entry",
				"posting_date": today(),
				"posting_time": nowtime(),
				"qty": 10,
				"batches": frappe._dict({batch_no: 10}),
				"type_of_transaction": "Inward",
				"do_not_submit": True,
			}
		)

		se.append(
			"items",
			{
				"item_code": item_code,
				"t_warehouse": "_Test Warehouse - _TC",
				"stock_uom": "Nos",
				"stock_qty": 10,
				"conversion_factor": 1,
				"uom": "Nos",
				"basic_rate": 500,
				"qty": 10,
				"use_serial_batch_fields": 0,
				"serial_and_batch_bundle": bundle_doc.name,
			},
		)

		se.save()

		bundle_doc = frappe.get_doc("Serial and Batch Bundle", bundle_doc.name)
		self.assertEqual(bundle_doc.voucher_detail_no, se.items[1].name)

		se.remove(se.items[1])
		se.save()
		self.assertEqual(len(se.items), 1)
		se.submit()

		bundle_doc.reload()
		self.assertEqual(bundle_doc.docstatus, 0)
		self.assertRaises(frappe.ValidationError, bundle_doc.submit)

	@ERPNextTestSuite.change_settings("Stock Settings", {"do_not_use_batchwise_valuation": 0})
	def test_amended_material_receipt_rate_after_batch_selection(self):
		warehouse = "_Test Warehouse - _TC"
		for valuation_method in ("FIFO", "Moving Average"):
			with self.subTest(valuation_method=valuation_method):
				item = make_item(
					properties={
						"is_stock_item": 1,
						"has_batch_no": 1,
						"stock_uom": "Nos",
						"valuation_method": valuation_method,
					}
				)
				batches = [
					frappe.get_doc(
						{"doctype": "Batch", "item": item.name, "batch_id": f"{item.name}-{index}"}
					)
					.insert()
					.name
					for index in range(2)
				]
				for index, (batch, qty) in enumerate(((batches[0], 10), (batches[1], 10), (batches[0], 5))):
					receipt = make_stock_entry(
						item_code=item.name,
						company="_Test Company",
						to_warehouse=warehouse,
						qty=qty,
						rate=10,
						batch_no=batch,
						posting_date=add_days(today(), index - 2),
						posting_time="10:00:00",
					)

				receipt.cancel()
				amended = frappe.copy_doc(receipt, ignore_no_copy=False)
				amended.amended_from = receipt.name
				amended.docstatus = 0
				row = amended.items[0]
				row.batch_no = None
				row.serial_and_batch_bundle = None
				row.use_serial_batch_fields = 0

				# The selector returns an unpriced bundle and copies its rate to the receipt row.
				bundle = add_serial_batch_ledgers(
					[{"batch_no": batches[1], "qty": 5}],
					row.as_dict(),
					amended.as_dict(),
					warehouse,
				)
				row.serial_and_batch_bundle = bundle.name
				row.basic_rate = bundle.avg_rate
				amended.insert()
				self.assertEqual(row.basic_rate, 10)
				self.assertEqual(row.basic_amount, 50)

				amended.submit()
				ledger = frappe.get_doc("Stock Ledger Entry", {"voucher_no": amended.name, "is_cancelled": 0})
				self.assertEqual(ledger.incoming_rate, 10)
				self.assertEqual(ledger.stock_value_difference, 50)
				self.assertEqual(ledger.stock_value, 250)

	def test_reference_voucher_on_cancel(self):
		"""
		When a source document is cancelled, the reference voucher field
		in the respective serial or batch document should be nullified.
		"""

		item_code = make_item(
			"Serial Item",
			properties={
				"is_stock_item": 1,
				"has_serial_no": 1,
				"serial_no_series": "SERIAL.#####",
			},
		).name

		se = make_stock_entry(
			item_code=item_code,
			qty=1,
			target="_Test Warehouse - _TC",
		)
		serial_no = get_serial_nos_from_bundle(se.items[0].serial_and_batch_bundle)[0]
		self.assertEqual(frappe.get_value("Serial No", serial_no, "reference_name"), se.name)

		se.cancel()
		self.assertIsNone(frappe.get_value("Serial No", serial_no, "reference_name"))

		se1 = frappe.copy_doc(se, ignore_no_copy=False)
		se1.items[0].serial_no = frappe.db.get_value("Serial No", serial_no, "serial_no")
		se1.submit()

		self.assertEqual(frappe.get_value("Serial No", serial_no, "reference_name"), se1.name)

	def test_stock_queue_for_return_entry_with_non_batchwise_valuation(self):
		from erpnext.controllers.sales_and_purchase_return import make_return_doc
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		batch_item_code = "Old Batch Return Queue Test"
		make_item(
			batch_item_code,
			{
				"has_batch_no": 1,
				"batch_number_series": "TEST-RET-Q-.#####",
				"create_new_batch": 1,
				"is_stock_item": 1,
				"valuation_method": "FIFO",
			},
		)

		batch_id = "Old Batch Return Queue 1"
		if not frappe.db.exists("Batch", batch_id):
			batch_doc = frappe.get_doc(
				{
					"doctype": "Batch",
					"batch_id": batch_id,
					"item": batch_item_code,
					"use_batchwise_valuation": 0,
				}
			).insert(ignore_permissions=True, set_name=batch_id)

			batch_doc.db_set(
				{
					"use_batchwise_valuation": 0,
					"batch_qty": 0,
				}
			)

		# Create initial stock with FIFO queue: [[10, 100], [20, 200]]
		make_stock_entry(
			item_code=batch_item_code,
			target="_Test Warehouse - _TC",
			qty=10,
			rate=100,
			batch_no=batch_id,
			use_serial_batch_fields=True,
		)

		make_stock_entry(
			item_code=batch_item_code,
			target="_Test Warehouse - _TC",
			qty=20,
			rate=200,
			batch_no=batch_id,
			use_serial_batch_fields=True,
		)

		# Purchase Receipt: inward 5 @ 300
		pr = make_purchase_receipt(
			item_code=batch_item_code,
			warehouse="_Test Warehouse - _TC",
			qty=5,
			rate=300,
			batch_no=batch_id,
			use_serial_batch_fields=True,
		)

		sle = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": batch_item_code, "is_cancelled": 0, "voucher_no": pr.name},
			["stock_queue"],
			as_dict=True,
		)

		# Stock queue should now be [[10, 100], [20, 200], [5, 300]]
		self.assertEqual(json.loads(sle.stock_queue), [[10, 100], [20, 200], [5, 300]])

		# Purchase Return: return 5 against the PR
		return_pr = make_return_doc("Purchase Receipt", pr.name)
		return_pr.submit()

		return_sle = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": batch_item_code, "is_cancelled": 0, "voucher_no": return_pr.name},
			["stock_queue"],
			as_dict=True,
		)

		# Stock queue should have 5 removed via FIFO from [[10, 100], [20, 200], [5, 300]]
		# FIFO removes from front: [10, 100] -> [5, 100], rest unchanged
		self.assertEqual(json.loads(return_sle.stock_queue), [[5, 100], [20, 200], [5, 300]])

	def test_stock_queue_for_return_entry_with_empty_fifo_queue(self):
		"""Credit note (sales return) against empty FIFO queue should still rebuild stock_queue."""
		from erpnext.controllers.sales_and_purchase_return import make_return_doc
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

		batch_item_code = "Old Batch Empty Queue Test"
		make_item(
			batch_item_code,
			{
				"has_batch_no": 1,
				"batch_number_series": "TEST-EQ-.#####",
				"create_new_batch": 1,
				"is_stock_item": 1,
				"valuation_method": "FIFO",
			},
		)

		batch_id = "Old Batch Empty Queue 1"
		if not frappe.db.exists("Batch", batch_id):
			batch_doc = frappe.get_doc(
				{
					"doctype": "Batch",
					"batch_id": batch_id,
					"item": batch_item_code,
					"use_batchwise_valuation": 0,
				}
			).insert(ignore_permissions=True, set_name=batch_id)

			batch_doc.db_set(
				{
					"use_batchwise_valuation": 0,
					"batch_qty": 0,
				}
			)

		# Inward 10 @ 100, then outward all 10 to empty the queue
		make_stock_entry(
			item_code=batch_item_code,
			target="_Test Warehouse - _TC",
			qty=10,
			rate=100,
			batch_no=batch_id,
			use_serial_batch_fields=True,
		)

		dn = create_delivery_note(
			item_code=batch_item_code,
			warehouse="_Test Warehouse - _TC",
			qty=10,
			rate=150,
			batch_no=batch_id,
			use_serial_batch_fields=True,
		)

		# Verify queue is empty after full outward
		sle = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": batch_item_code, "is_cancelled": 0, "voucher_no": dn.name},
			["stock_queue"],
			as_dict=True,
		)
		self.assertFalse(json.loads(sle.stock_queue or "[]"))

		# Sales return (credit note): 5 items come back at original rate 100
		return_dn = make_return_doc("Delivery Note", dn.name)
		for row in return_dn.items:
			row.qty = -5
		return_dn.save().submit()

		return_sle = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": batch_item_code, "is_cancelled": 0, "voucher_no": return_dn.name},
			["stock_queue"],
			as_dict=True,
		)

		# Stock queue should have the returned stock: [[5, 100]]
		self.assertEqual(json.loads(return_sle.stock_queue), [[5, 100]])

	def test_get_picked_batches_runs(self):
		from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import get_picked_batches

		# Sum(qty) is selected with bare batch_no/warehouse; without a GROUP BY this
		# raises a GroupingError on Postgres (and collapses to one arbitrary row on
		# MariaDB). It must run and return a per-(batch, warehouse) mapping on both.
		result = get_picked_batches(frappe._dict())
		self.assertIsInstance(result, dict)

	def _assert_legacy_return_valuation(self, item_code, props, batch_no=None):
		"""Return against a legacy serial/batch receipt (no Serial and Batch Bundle) must value outgoing stock from the original ledger rate."""
		from erpnext.controllers.sales_and_purchase_return import make_return_doc
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		make_item(item_code, props)
		if batch_no and not frappe.db.exists("Batch", {"item": item_code, "batch_id": batch_no}):
			frappe.get_doc({"doctype": "Batch", "batch_id": batch_no, "item": item_code}).insert()
		if batch_no:
			batch_no = frappe.db.get_value("Batch", {"item": item_code, "batch_id": batch_no}, "name")

		pr = make_purchase_receipt(
			item_code=item_code, qty=10, rate=100, batch_no=batch_no, use_serial_batch_fields=True
		)

		# Simulate a receipt migrated from an older version: serial nos / batch tracked via the
		# deprecated fields on the Stock Ledger Entry, with no Serial and Batch Bundle.
		serial_nos = []
		for row in pr.items:
			if row.serial_and_batch_bundle:
				serial_nos = frappe.get_all(
					"Serial and Batch Entry",
					filters={"parent": row.serial_and_batch_bundle},
					pluck="serial_no",
				)
				frappe.db.delete("Serial and Batch Bundle", {"name": row.serial_and_batch_bundle})
				frappe.db.set_value("Purchase Receipt Item", row.name, "serial_and_batch_bundle", None)

		serial_nos = [sn for sn in serial_nos if sn]
		legacy = {"serial_and_batch_bundle": None}
		if batch_no:
			legacy["batch_no"] = batch_no
		if serial_nos:
			legacy["serial_no"] = "\n".join(serial_nos)
		for sle in frappe.get_all("Stock Ledger Entry", filters={"voucher_no": pr.name}, pluck="name"):
			frappe.db.set_value("Stock Ledger Entry", sle, legacy)

		rt = make_return_doc("Purchase Receipt", pr.name)
		rt.items[0].qty = -4
		rt.items[0].received_qty = -4
		rt.items[0].use_serial_batch_fields = 1
		if batch_no:
			rt.items[0].batch_no = batch_no
		if serial_nos:
			rt.items[0].serial_no = "\n".join(
				frappe.db.get_value("Serial No", serial_id, "serial_no") for serial_id in serial_nos[:4]
			)
		rt.submit()

		difference_in_stock_value = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_no": rt.name, "is_cancelled": 0, "voucher_type": "Purchase Receipt"},
			"stock_value_difference",
		)
		# 4 units returned at the original ledger rate of 100 -> -400 (must not be zero)
		self.assertEqual(flt(difference_in_stock_value, 2), -400.0)

	def test_return_valuation_for_legacy_batch_without_bundle(self):
		self._assert_legacy_return_valuation(
			"Test Legacy Batch Return Valuation",
			{
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "LBRV-.#####",
				"is_stock_item": 1,
			},
			batch_no="LBRV-BATCH-0001",
		)

	def test_return_valuation_for_legacy_serial_without_bundle(self):
		self._assert_legacy_return_valuation(
			"Test Legacy Serial Return Valuation",
			{"has_serial_no": 1, "serial_no_series": "LSRV-.#####", "is_stock_item": 1},
		)

	def test_return_valuation_for_legacy_serial_and_batch_without_bundle(self):
		self._assert_legacy_return_valuation(
			"Test Legacy Serial Batch Return Valuation",
			{
				"has_serial_no": 1,
				"serial_no_series": "LSBRV-.#####",
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "LSBRVB-.#####",
				"is_stock_item": 1,
			},
			batch_no="LSBRV-BATCH-0001",
		)

	def _setup_negative_batch_item(self, item_code, batches):
		make_item(item_code, properties={"is_stock_item": 1, "has_batch_no": 1})
		batch_ids = []
		for batch_no in batches:
			if not frappe.db.exists("Batch", {"item": item_code, "batch_id": batch_no}):
				frappe.get_doc(
					{"doctype": "Batch", "batch_id": batch_no, "item": item_code, "company": "_Test Company"}
				).insert(ignore_permissions=True)
			batch_ids.append(frappe.db.get_value("Batch", {"item": item_code, "batch_id": batch_no}, "name"))
		return batch_ids

	def _allow_negative_stock_temporarily(self):
		for field in ("allow_negative_stock", "allow_negative_stock_for_batch"):
			frappe.db.set_single_value("Stock Settings", field, 1)

	def _disable_negative_stock(self):
		frappe.db.set_single_value("Stock Settings", "allow_negative_stock", 0)
		frappe.db.set_single_value("Stock Settings", "allow_negative_stock_for_batch", 0)

	def test_historical_negative_batch_stock_does_not_block_outward(self):
		from unittest.mock import patch

		from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
			BatchNegativeStockError,
			SerialandBatchBundle,
		)

		item_code = "Test Hist Neg Batch Item"
		ballast_batch, batch_no = "THNB-BALLAST-001", "THNB-BATCH-001"
		ballast_batch, batch_no = self._setup_negative_batch_item(item_code, [ballast_batch, batch_no])
		warehouse = "_Test Warehouse - _TC"

		self._allow_negative_stock_temporarily()
		make_stock_entry(
			item_code=item_code,
			qty=1000,
			rate=100,
			target=warehouse,
			use_serial_batch_fields=True,
			batch_no=ballast_batch,
			posting_date=add_days(today(), -730),
			posting_time="10:00:00",
		)
		make_stock_entry(
			item_code=item_code,
			qty=100,
			rate=100,
			target=warehouse,
			use_serial_batch_fields=True,
			batch_no=batch_no,
			posting_date=add_days(today(), -365),
			posting_time="10:00:00",
		)
		with patch.object(SerialandBatchBundle, "validate_negative_batch"):
			make_stock_entry(
				item_code=item_code,
				qty=5,
				source=warehouse,
				use_serial_batch_fields=True,
				batch_no=batch_no,
				posting_date=add_days(today(), -730),
				posting_time="11:00:00",
			)
		self._disable_negative_stock()

		make_stock_entry(
			item_code=item_code,
			qty=10,
			source=warehouse,
			use_serial_batch_fields=True,
			batch_no=batch_no,
		)

		outward = make_stock_entry(
			item_code=item_code,
			qty=200,
			source=warehouse,
			use_serial_batch_fields=True,
			batch_no=batch_no,
			do_not_submit=True,
		)
		self.assertRaises(BatchNegativeStockError, outward.submit)

	def test_backdated_outward_cannot_make_future_batch_stock_negative(self):
		from erpnext.stock.stock_ledger import NegativeStockError

		item_code = "Test Future Neg Batch Item"
		ballast_batch, batch_no = "TFNB-BALLAST-001", "TFNB-BATCH-001"
		ballast_batch, batch_no = self._setup_negative_batch_item(item_code, [ballast_batch, batch_no])
		warehouse = "_Test Warehouse - _TC"

		make_stock_entry(
			item_code=item_code,
			qty=1000,
			rate=100,
			target=warehouse,
			use_serial_batch_fields=True,
			batch_no=ballast_batch,
			posting_date=add_days(today(), -365),
			posting_time="10:00:00",
		)
		make_stock_entry(
			item_code=item_code,
			qty=100,
			rate=100,
			target=warehouse,
			use_serial_batch_fields=True,
			batch_no=batch_no,
			posting_date=add_days(today(), -365),
			posting_time="11:00:00",
		)
		make_stock_entry(
			item_code=item_code,
			qty=90,
			source=warehouse,
			use_serial_batch_fields=True,
			batch_no=batch_no,
			posting_date=add_days(today(), -180),
			posting_time="10:00:00",
		)
		make_stock_entry(
			item_code=item_code,
			qty=60,
			rate=100,
			target=warehouse,
			use_serial_batch_fields=True,
			batch_no=batch_no,
			posting_date=add_days(today(), -30),
			posting_time="10:00:00",
		)

		make_stock_entry(
			item_code=item_code,
			qty=5,
			source=warehouse,
			use_serial_batch_fields=True,
			batch_no=batch_no,
			posting_date=add_days(today(), -240),
			posting_time="10:00:00",
		)

		backdated = make_stock_entry(
			item_code=item_code,
			qty=50,
			source=warehouse,
			use_serial_batch_fields=True,
			batch_no=batch_no,
			posting_date=add_days(today(), -240),
			posting_time="11:00:00",
			do_not_submit=True,
		)
		self.assertRaises(NegativeStockError, backdated.submit)

	def make_serial_item_for_valuation(self, item_code, use_serial_no_wise_valuation):
		return make_item(
			item_code,
			{
				"is_stock_item": 1,
				"has_serial_no": 1,
				"serial_no_series": item_code + "-.####",
				"valuation_method": "FIFO" if use_serial_no_wise_valuation else "Moving Average",
				"use_serial_no_wise_valuation": use_serial_no_wise_valuation,
			},
		)

	def receive_serial_stock(self, item_code, qty, rate, warehouse, posting_date=None):
		entry = make_stock_entry(
			item_code=item_code,
			target=warehouse,
			qty=qty,
			basic_rate=rate,
			posting_date=posting_date,
			use_serial_batch_fields=1,
		)

		return get_serial_nos_from_bundle(entry.items[0].serial_and_batch_bundle)

	def issue_serial_no(self, item_code, serial_no, warehouse, posting_date=None):
		return make_stock_entry(
			item_code=item_code,
			source=warehouse,
			qty=1,
			serial_no=serial_no,
			posting_date=posting_date,
			use_serial_batch_fields=1,
		)

	def get_stock_value_difference(self, voucher_no):
		return frappe.db.get_value(
			"Stock Ledger Entry", {"voucher_no": voucher_no, "is_cancelled": 0}, "stock_value_difference"
		)

	def test_serial_no_wise_valuation_uses_serial_rate_when_enabled(self):
		warehouse = "_Test Warehouse - _TC"
		item = self.make_serial_item_for_valuation("_Test Serial Wise Valuation On", 1)

		self.receive_serial_stock(item.name, 2, 100, warehouse)
		newer_serial_nos = self.receive_serial_stock(item.name, 2, 200, warehouse)

		issue = self.issue_serial_no(item.name, newer_serial_nos[-1], warehouse)

		self.assertEqual(flt(self.get_stock_value_difference(issue.name)), -200.0)

	def test_serial_no_wise_valuation_uses_item_valuation_method_when_disabled(self):
		warehouse = "_Test Warehouse - _TC"
		item = self.make_serial_item_for_valuation("_Test Serial Wise Valuation Off", 0)

		self.receive_serial_stock(item.name, 2, 100, warehouse)
		newer_serial_nos = self.receive_serial_stock(item.name, 2, 200, warehouse)

		issue = self.issue_serial_no(item.name, newer_serial_nos[-1], warehouse)

		self.assertEqual(flt(self.get_stock_value_difference(issue.name)), -150.0)

	def test_outward_bundle_rate_not_set_when_serial_no_wise_valuation_disabled(self):
		warehouse = "_Test Warehouse - _TC"
		item = self.make_serial_item_for_valuation("_Test Serial Wise Valuation No Rate", 0)

		serial_nos = self.receive_serial_stock(item.name, 2, 100, warehouse)
		issue = self.issue_serial_no(item.name, serial_nos[-1], warehouse)

		rates = frappe.get_all(
			"Serial and Batch Entry",
			filters={"parent": issue.items[0].serial_and_batch_bundle},
			pluck="incoming_rate",
		)

		self.assertTrue(rates)
		for rate in rates:
			self.assertEqual(flt(rate), 0.0)

	def test_cannot_enable_serial_no_wise_valuation_when_serial_nos_exist(self):
		warehouse = "_Test Warehouse - _TC"
		item = self.make_serial_item_for_valuation("_Test Serial Wise Valuation Toggle", 1)
		self.receive_serial_stock(item.name, 1, 100, warehouse)

		item.reload()
		item.use_serial_no_wise_valuation = 0
		item.save()

		item.reload()
		item.use_serial_no_wise_valuation = 1
		self.assertRaises(frappe.ValidationError, item.save)

	def make_purchase_return_for_serial_no(self, item_code, serial_no, receipt):
		from erpnext.controllers.sales_and_purchase_return import make_return_doc

		entry = make_return_doc("Purchase Receipt", receipt.name)
		entry.items[0].qty = -1
		entry.items[0].received_qty = -1
		for row in entry.items:
			row.serial_and_batch_bundle = None
			row.use_serial_batch_fields = 1
			row.serial_no = serial_no

		entry.save()
		entry.submit()

		return entry

	def test_purchase_return_uses_item_valuation_method_when_disabled(self):
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		warehouse = "_Test Warehouse - _TC"
		item = self.make_serial_item_for_valuation("_Test Serial Wise Valuation Pur Return Off", 0)

		make_purchase_receipt(item_code=item.name, qty=2, rate=100, warehouse=warehouse)
		costlier_receipt = make_purchase_receipt(item_code=item.name, qty=2, rate=200, warehouse=warehouse)
		serial_nos = get_serial_nos_from_bundle(costlier_receipt.items[0].serial_and_batch_bundle)

		entry = self.make_purchase_return_for_serial_no(item.name, serial_nos[-1], costlier_receipt)

		self.assertEqual(flt(self.get_stock_value_difference(entry.name)), -150.0)

	def test_purchase_return_uses_serial_rate_when_enabled(self):
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		warehouse = "_Test Warehouse - _TC"
		item = self.make_serial_item_for_valuation("_Test Serial Wise Valuation Pur Return On", 1)

		make_purchase_receipt(item_code=item.name, qty=2, rate=100, warehouse=warehouse)
		costlier_receipt = make_purchase_receipt(item_code=item.name, qty=2, rate=200, warehouse=warehouse)
		serial_nos = get_serial_nos_from_bundle(costlier_receipt.items[0].serial_and_batch_bundle)

		entry = self.make_purchase_return_for_serial_no(item.name, serial_nos[-1], costlier_receipt)

		self.assertEqual(flt(self.get_stock_value_difference(entry.name)), -200.0)

	def deliver_serial_no(self, item_code, serial_no, warehouse, posting_date=None):
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

		return create_delivery_note(
			item_code=item_code,
			warehouse=warehouse,
			qty=1,
			serial_no=serial_no,
			posting_date=posting_date,
			use_serial_batch_fields=1,
		)

	def repost_item_and_warehouse(self, item_code, warehouse, posting_date):
		from erpnext.stock.doctype.repost_item_valuation.repost_item_valuation import repost

		riv = frappe.get_doc(
			{
				"doctype": "Repost Item Valuation",
				"based_on": "Item and Warehouse",
				"item_code": item_code,
				"warehouse": warehouse,
				"posting_date": posting_date,
				"posting_time": "00:00:01",
				"company": frappe.get_cached_value("Warehouse", warehouse, "company"),
			}
		)
		riv.flags.dont_run_in_test = True
		riv.submit()
		riv.reload()
		repost(riv)
		riv.reload()
		self.assertEqual(riv.status, "Completed")

	def assert_outward_sle_at_moving_average(self, voucher_no, warehouse, rate, qty_after_transaction):
		sle = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_no": voucher_no, "warehouse": warehouse, "is_cancelled": 0},
			["outgoing_rate", "valuation_rate", "stock_value", "stock_value_difference"],
			as_dict=True,
		)

		self.assertEqual(flt(sle.outgoing_rate), rate, voucher_no)
		self.assertEqual(flt(sle.valuation_rate), rate, voucher_no)
		self.assertEqual(flt(sle.stock_value), rate * qty_after_transaction, voucher_no)
		self.assertEqual(flt(sle.stock_value_difference), -rate, voucher_no)

	def test_repost_values_outward_entries_at_moving_average_when_disabled(self):
		"""A repost must value plain outward entries at the moving average once the switch is off. The
		serial rates are seeded because such entries come from ledgers written before the switch."""
		warehouse = "_Test Warehouse - _TC"
		item = self.make_serial_item_for_valuation("_Test Serial Wise Valuation Repost Outward", 1)
		posting_date = add_days(today(), -10)

		cheaper = self.receive_serial_stock(item.name, 2, 100, warehouse, posting_date)
		costlier = self.receive_serial_stock(item.name, 2, 200, warehouse, add_days(posting_date, 1))

		issue = self.issue_serial_no(item.name, costlier[-1], warehouse, add_days(posting_date, 2))
		delivery = self.deliver_serial_no(item.name, cheaper[-1], warehouse, add_days(posting_date, 3))

		for voucher_no, serial_rate in ((issue.name, 200.0), (delivery.name, 100.0)):
			sle_name = frappe.db.get_value(
				"Stock Ledger Entry", {"voucher_no": voucher_no, "is_cancelled": 0}, "name"
			)
			frappe.db.set_value(
				"Stock Ledger Entry", sle_name, "outgoing_rate", serial_rate, update_modified=False
			)

		item.reload()
		item.use_serial_no_wise_valuation = 0
		item.save()

		self.repost_item_and_warehouse(item.name, warehouse, posting_date)

		# 2 @ 100 plus 2 @ 200 makes the moving average 150, and neither outward entry may move it
		self.assert_outward_sle_at_moving_average(issue.name, warehouse, 150.0, 3.0)
		self.assert_outward_sle_at_moving_average(delivery.name, warehouse, 150.0, 2.0)

	def test_repost_values_purchase_return_at_moving_average_when_disabled(self):
		"""Same as above for a purchase return: it must leave the remaining stock at the moving average,
		not at the returned serial's own rate."""
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		warehouse = "_Test Warehouse - _TC"
		item = self.make_serial_item_for_valuation("_Test Serial Wise Valuation Repost Return", 1)
		posting_date = add_days(today(), -10)

		make_purchase_receipt(
			item_code=item.name, qty=2, rate=100, warehouse=warehouse, posting_date=posting_date
		)
		costlier_receipt = make_purchase_receipt(
			item_code=item.name,
			qty=2,
			rate=200,
			warehouse=warehouse,
			posting_date=add_days(posting_date, 1),
		)
		serial_nos = get_serial_nos_from_bundle(costlier_receipt.items[0].serial_and_batch_bundle)

		entry = self.make_purchase_return_for_serial_no(item.name, serial_nos[-1], costlier_receipt)
		self.assertEqual(flt(self.get_stock_value_difference(entry.name)), -200.0)

		item.reload()
		item.use_serial_no_wise_valuation = 0
		item.save()

		self.repost_item_and_warehouse(item.name, warehouse, posting_date)

		self.assert_outward_sle_at_moving_average(entry.name, warehouse, 150.0, 3.0)

	def test_valuation_method_forced_to_moving_average_when_disabled(self):
		item = self.make_serial_item_for_valuation("_Test Serial Wise Valuation Forced MA", 1)
		self.receive_serial_stock(item.name, 1, 100, "_Test Warehouse - _TC")

		item.reload()
		item.valuation_method = "FIFO"
		item.use_serial_no_wise_valuation = 0
		item.save()

		item.reload()
		self.assertEqual(item.valuation_method, "Moving Average")

	def test_valuation_method_kept_when_disabled_without_stock_transactions(self):
		item = self.make_serial_item_for_valuation("_Test Serial Wise Valuation No MA Yet", 1)

		item.reload()
		item.valuation_method = "FIFO"
		item.use_serial_no_wise_valuation = 0
		item.save()

		item.reload()
		self.assertEqual(item.valuation_method, "FIFO")

	def test_valuation_method_kept_when_disabled_and_saved_after_stock_transactions(self):
		"""An item that has always had the switch off keeps its own valuation method. Only turning the
		switch off forces Moving Average, so an unrelated save cannot silently revalue the ledger."""
		item = self.make_serial_item_for_valuation("_Test Serial Wise Valuation Keeps FIFO On Save", 0)
		item.reload()
		item.valuation_method = "FIFO"
		item.save()

		self.receive_serial_stock(item.name, 2, 100, "_Test Warehouse - _TC")
		self.receive_serial_stock(item.name, 2, 200, "_Test Warehouse - _TC")

		item.reload()
		item.description = "saved for an unrelated reason"
		item.save()

		item.reload()
		self.assertEqual(item.valuation_method, "FIFO")

	def test_fifo_allowed_when_disabled_without_stock_transactions(self):
		item = self.make_serial_item_for_valuation("_Test Serial Wise Valuation FIFO Ok", 0)

		item.reload()
		item.valuation_method = "FIFO"
		item.save()

		item.reload()
		self.assertEqual(item.valuation_method, "FIFO")

	def test_first_transaction_uses_moving_average_when_disabled(self):
		from collections import defaultdict

		from erpnext.stock.utils import get_valuation_method

		item = self.make_serial_item_for_valuation("_Test Serial Wise Valuation First Txn", 0)
		warehouse = "_Test Warehouse - _TC"

		item.reload()
		item.valuation_method = "FIFO"
		item.save()

		previous_cache = getattr(frappe.local, "request_cache", None)
		self.addCleanup(setattr, frappe.local, "request_cache", previous_cache)
		frappe.local.request_cache = defaultdict(dict)

		# Any method may be stored and used while the item has no ledger. Reading it here also
		# primes the request cache with FIFO, the way validate() does before entries exist.
		self.assertEqual(item.valuation_method, "FIFO")
		self.assertEqual(get_valuation_method(item.name), "FIFO")

		serial_nos = self.receive_serial_stock(item.name, 1, 100, warehouse)
		self.receive_serial_stock(item.name, 1, 200, warehouse)

		# The issue must be valued at the moving average of 150, not the FIFO rate of 100, even
		# though the cache primed above still holds FIFO.
		entry = self.issue_serial_no(item.name, serial_nos[0], warehouse)
		stock_value_difference = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_no": entry.name, "is_cancelled": 0},
			"stock_value_difference",
		)
		self.assertEqual(flt(stock_value_difference, 2), -100.0)

		# Posting stock does not save the item, so the stored method stays FIFO while the
		# effective method is Moving Average now that a ledger exists.
		item.reload()
		self.assertEqual(item.valuation_method, "FIFO")
		frappe.local.request_cache = defaultdict(dict)
		self.assertEqual(get_valuation_method(item.name), "FIFO")

	def test_legacy_serial_no_lookup_is_case_insensitive(self):
		# MariaDB matches serial_no under a case insensitive collation, PostgreSQL does not.
		# This asserts the lookup behaves the same on both; it can only fail on PostgreSQL.
		from erpnext.stock.deprecated_serial_batch import DeprecatedSerialNoValuation

		item = self.make_serial_item_for_valuation("_Test Legacy Serial Case", 1)
		warehouse = "_Test Warehouse - _TC"
		serial_no = self.receive_serial_stock(item.name, 1, 100, warehouse)[0]

		# Rewrite the receipt into the pre-bundle representation.
		sles = frappe.get_all(
			"Stock Ledger Entry",
			filters={"item_code": item.name, "is_cancelled": 0},
			fields=["name", "posting_datetime"],
		)
		for sle in sles:
			frappe.db.set_value(
				"Stock Ledger Entry", sle.name, {"serial_and_batch_bundle": None, "serial_no": serial_no}
			)

		class LegacyLookup(DeprecatedSerialNoValuation):
			def __init__(self, sle):
				self.sle = sle

		lookup = LegacyLookup(
			frappe._dict(
				item_code=item.name,
				company=frappe.get_cached_value("Warehouse", warehouse, "company"),
				warehouse=warehouse,
			)
		)
		posting_datetime = sles[0].posting_datetime

		self.assertTrue(lookup.get_last_inward_sle_for_serial_no(serial_no, posting_datetime))
		self.assertTrue(lookup.get_last_inward_sle_for_serial_no(serial_no.swapcase(), posting_datetime))

	def test_cannot_set_fifo_when_serial_no_wise_valuation_disabled(self):
		item = self.make_serial_item_for_valuation("_Test Serial Wise Valuation No FIFO", 0)
		self.receive_serial_stock(item.name, 1, 100, "_Test Warehouse - _TC")

		item.reload()
		self.assertEqual(item.valuation_method, "Moving Average")

		item.valuation_method = "FIFO"
		self.assertRaises(frappe.ValidationError, item.save)

	def test_valuation_helpers_not_stale_after_disabling_in_same_request(self):
		from collections import defaultdict

		from erpnext.stock.utils import get_valuation_method, is_serial_no_wise_valuation_disabled

		item = self.make_serial_item_for_valuation("_Test Serial Wise Valuation Cache", 1)
		self.receive_serial_stock(item.name, 1, 100, "_Test Warehouse - _TC")

		previous_cache = getattr(frappe.local, "request_cache", None)
		self.addCleanup(setattr, frappe.local, "request_cache", previous_cache)
		frappe.local.request_cache = defaultdict(dict)

		self.assertEqual(get_valuation_method(item.name), "FIFO")
		self.assertFalse(is_serial_no_wise_valuation_disabled(item.name))

		item.reload()
		item.use_serial_no_wise_valuation = 0
		item.save()

		self.assertEqual(get_valuation_method(item.name), "Moving Average")
		self.assertTrue(is_serial_no_wise_valuation_disabled(item.name))

	def test_valuation_method_untouched_when_serial_no_wise_valuation_enabled(self):
		item = self.make_serial_item_for_valuation("_Test Serial Wise Valuation Keeps FIFO", 1)

		item.reload()
		self.assertEqual(item.valuation_method, "FIFO")

	def test_enable_serial_no_wise_valuation_allowed_without_serial_nos(self):
		item = self.make_serial_item_for_valuation("_Test Serial Wise Valuation No Serials", 0)

		item.reload()
		item.use_serial_no_wise_valuation = 1
		item.save()

		item.reload()
		self.assertEqual(item.use_serial_no_wise_valuation, 1)


def get_batch_from_bundle(bundle):
	from erpnext.stock.serial_batch_bundle import get_batch_nos

	batches = get_batch_nos(bundle)

	return next(iter(batches.keys()))


def get_serial_nos_from_bundle(bundle):
	from erpnext.stock.serial_batch_bundle import get_serial_nos

	serial_nos = get_serial_nos(bundle)
	return sorted(serial_nos) if serial_nos else []


def get_serial_numbers_from_bundle(bundle):
	return frappe.get_all(
		"Serial No",
		filters={"name": ("in", get_serial_nos_from_bundle(bundle))},
		pluck="serial_no",
		order_by="serial_no",
	)


def make_serial_batch_bundle(kwargs):
	from erpnext.stock.serial_batch_bundle import SerialBatchCreation

	if isinstance(kwargs, dict):
		kwargs = frappe._dict(kwargs)

	type_of_transaction = "Inward" if kwargs.qty > 0 else "Outward"
	if kwargs.get("type_of_transaction"):
		type_of_transaction = kwargs.get("type_of_transaction")

	posting_datetime = None
	if kwargs.get("posting_date"):
		posting_datetime = combine_datetime(kwargs.posting_date, kwargs.posting_time or nowtime())

	company = kwargs.get("company")
	if not company and kwargs.get("warehouse"):
		company = frappe.get_cached_value("Warehouse", kwargs.warehouse, "company")

	sb = SerialBatchCreation(
		{
			"item_code": kwargs.item_code,
			"warehouse": kwargs.warehouse,
			"voucher_type": kwargs.voucher_type,
			"voucher_no": kwargs.voucher_no,
			"posting_datetime": posting_datetime,
			"qty": kwargs.qty,
			"avg_rate": kwargs.rate,
			"batches": kwargs.batches,
			"serial_nos": kwargs.serial_nos,
			"type_of_transaction": type_of_transaction,
			"company": company or "_Test Company",
			"do_not_submit": kwargs.do_not_submit,
			"ignore_sabb_validation": kwargs.ignore_sabb_validation or False,
		}
	)

	if not kwargs.get("do_not_save"):
		return sb.make_serial_and_batch_bundle()

	return sb


class TestSerialandBatchBundleLogic(ERPNextTestSuite):
	"""Pure helpers and in-memory document validations, covering branches the
	integration suite doesn't reach (no stock-ledger / serial / batch fixtures)."""

	def test_parse_serial_nos_splits_and_trims(self):
		self.assertEqual(parse_serial_nos("SN1\nSN2"), ["SN1", "SN2"])
		self.assertEqual(parse_serial_nos("SN1, SN2 , SN3"), ["SN1", "SN2", "SN3"])
		# blanks are dropped and an existing list is returned unchanged
		self.assertEqual(parse_serial_nos("SN1,,\n , SN2"), ["SN1", "SN2"])
		self.assertEqual(parse_serial_nos(["SN1", "SN2"]), ["SN1", "SN2"])

	def test_get_qty_based_available_batches_allocates_across_batches(self):
		batches = [
			frappe._dict(batch_no="B1", qty=10, warehouse="W"),
			frappe._dict(batch_no="B2", qty=5, warehouse="W"),
		]
		# 12 consumes B1 fully then 2 from B2
		result = get_qty_based_available_batches(batches, 12)
		self.assertEqual([(b.batch_no, b.qty) for b in result], [("B1", 10), ("B2", 2)])
		# 8 is satisfied by B1 alone; B2 is not touched
		result = get_qty_based_available_batches(batches, 8)
		self.assertEqual([(b.batch_no, b.qty) for b in result], [("B1", 8)])

	def test_get_available_batches_qty_aggregates_by_batch(self):
		batches = [
			frappe._dict(batch_no="B1", qty=10),
			frappe._dict(batch_no="B2", qty=5),
			frappe._dict(batch_no="B1", qty=3),
		]
		agg = get_available_batches_qty(batches)
		self.assertEqual(agg["B1"], 13)
		self.assertEqual(agg["B2"], 5)

	def test_get_type_of_transaction_derives_direction(self):
		def se(**kw):
			return get_type_of_transaction(frappe._dict(doctype="Stock Entry"), frappe._dict(**kw))

		self.assertEqual(se(s_warehouse="W"), "Outward")  # issuing from a source warehouse
		self.assertEqual(se(), "Inward")  # only a target warehouse
		self.assertEqual(
			get_type_of_transaction(frappe._dict(doctype="Purchase Receipt"), frappe._dict()), "Inward"
		)
		self.assertEqual(
			get_type_of_transaction(frappe._dict(doctype="Stock Reconciliation"), frappe._dict()), "Inward"
		)
		# a purchase return reverses the direction to Outward
		self.assertEqual(
			get_type_of_transaction(frappe._dict(doctype="Purchase Receipt", is_return=1), frappe._dict()),
			"Outward",
		)

	def test_transaction_direction_ignores_row_override(self):
		cases = [
			("Delivery Note", {}, {}, "Outward"),
			("Sales Invoice", {"is_return": 1}, {}, "Inward"),
			("Purchase Receipt", {}, {}, "Inward"),
			("Purchase Invoice", {"is_return": 1}, {}, "Outward"),
			("Stock Entry", {}, {"s_warehouse": "Source", "t_warehouse": "Target"}, "Outward"),
			("Stock Entry", {}, {"t_warehouse": "Target"}, "Inward"),
			("Stock Reconciliation", {}, {}, "Inward"),
			("Subcontracting Receipt", {}, {"doctype": "Subcontracting Receipt Item"}, "Inward"),
			("Subcontracting Receipt", {}, {"doctype": "Subcontracting Receipt Supplied Item"}, "Outward"),
			(
				"Subcontracting Receipt",
				{"is_return": 1},
				{"doctype": "Subcontracting Receipt Supplied Item"},
				"Inward",
			),
			("Asset Repair", {}, {"consumed_quantity": 1}, "Outward"),
			("Asset Repair", {}, {"consumed_quantity": -1}, "Outward"),
			("Pick List", {}, {"qty": 1}, "Outward"),
			("Pick List", {}, {"qty": -1}, "Outward"),
		]
		for doctype, parent_values, row_values, expected in cases:
			parent = frappe._dict(doctype=doctype, **parent_values)
			row = frappe._dict(row_values)
			row.type_of_transaction = "Outward" if expected == "Inward" else "Inward"
			with self.subTest(doctype=doctype, parent=parent_values, row=row_values):
				self.assertEqual(get_type_of_transaction(parent, row), expected)
				self.assertNotEqual(row.type_of_transaction, expected)

	def test_duplicate_serial_no_in_entries_is_rejected(self):
		doc = frappe.new_doc("Serial and Batch Bundle")
		doc.append("entries", {"serial_no": "SN1"})
		doc.append("entries", {"serial_no": "SN1"})
		self.assertRaises(frappe.ValidationError, doc.validate_duplicate_serial_and_batch_no)

	def test_duplicate_batch_no_in_entries_is_rejected(self):
		doc = frappe.new_doc("Serial and Batch Bundle")
		doc.append("entries", {"batch_no": "B1"})
		doc.append("entries", {"batch_no": "B1"})
		self.assertRaises(frappe.ValidationError, doc.validate_duplicate_serial_and_batch_no)

	def test_voucher_no_is_mandatory(self):
		doc = frappe.new_doc("Serial and Batch Bundle")
		self.assertRaises(frappe.ValidationError, doc.validate_serial_and_batch_data)

	def test_validate_docstatus_rejects_unsubmitted_entries(self):
		doc = frappe.new_doc("Serial and Batch Bundle")
		doc.append("entries", {"qty": 1})  # a fresh row has docstatus 0
		self.assertRaises(frappe.ValidationError, doc.validate_docstatus)

	def test_calculate_total_qty_normalizes_and_signs(self):
		inward = frappe.new_doc("Serial and Batch Bundle")
		inward.type_of_transaction = "Inward"
		inward.append("entries", {"qty": 5})
		inward.append("entries", {"qty": 3})
		inward.calculate_total_qty(save=False)
		self.assertEqual(inward.total_qty, 8)

		# Outward flips the sign
		outward = frappe.new_doc("Serial and Batch Bundle")
		outward.type_of_transaction = "Outward"
		outward.append("entries", {"qty": 5})
		outward.calculate_total_qty(save=False)
		self.assertEqual(outward.total_qty, -5)

		# a serialized bundle normalizes each row qty to 1
		serialized = frappe.new_doc("Serial and Batch Bundle")
		serialized.has_serial_no = 1
		serialized.type_of_transaction = "Inward"
		serialized.append("entries", {"qty": 5})
		serialized.calculate_total_qty(save=False)
		self.assertEqual(serialized.total_qty, 1)

	def test_get_bundle_wise_serial_nos(self):
		from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
			get_bundle_wise_serial_nos,
		)

		item_code = make_item(properties={"has_serial_no": 1, "serial_no_series": "TEST-BWSN-.#####"}).name

		bundles = []
		for _ in range(2):
			se = make_stock_entry(
				item_code=item_code,
				target="_Test Warehouse - _TC",
				qty=3,
				rate=100,
			)
			bundles.append(se.items[0].serial_and_batch_bundle)

		data = [frappe._dict(serial_and_batch_bundle=bundle) for bundle in bundles]

		self.assertEqual(get_bundle_wise_serial_nos([], {}), {})

		bundle_wise_serial_nos = get_bundle_wise_serial_nos(data, {})
		for bundle in bundles:
			self.assertEqual(sorted(bundle_wise_serial_nos[bundle]), get_serial_nos_from_bundle(bundle))

		# check_serial_nos must restrict the result to the requested serial nos
		serial_no = get_serial_nos_from_bundle(bundles[0])[0]
		bundle_wise_serial_nos = get_bundle_wise_serial_nos(
			data, {"check_serial_nos": True, "serial_nos": [serial_no]}
		)

		self.assertNotIn(bundles[1], bundle_wise_serial_nos)
		self.assertEqual(bundle_wise_serial_nos[bundles[0]], [serial_no])

	@ERPNextTestSuite.change_settings(
		"Stock Settings", {"auto_create_serial_and_batch_bundle_for_outward": 1}
	)
	def test_batchwise_valuation_for_same_posting_datetime_entries(self):
		# an inward at a different rate and multiple outward rows with the same
		# item and warehouse share the same posting datetime, the tie-breaking
		# must include the same-timestamp entries which are already part of the
		# ledger and must not let the outward rows count each other
		item_code = make_item(
			"Test Batchwise Same Posting Datetime Item 1",
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "TBSPD-ITEM1-.#####",
				"valuation_method": "FIFO",
			},
		).name

		warehouse = "_Test Warehouse - _TC"

		receipt = make_stock_entry(
			item_code=item_code,
			qty=10,
			rate=100,
			target=warehouse,
			posting_date=add_days(today(), -5),
			posting_time="12:00:00",
		)

		batch_no = get_batch_from_bundle(receipt.items[0].serial_and_batch_bundle)
		self.assertTrue(frappe.db.get_value("Batch", batch_no, "use_batchwise_valuation"))

		# same posting datetime as the outward rows below, at a different rate
		make_stock_entry(
			item_code=item_code,
			qty=20,
			rate=250,
			target=warehouse,
			batch_no=batch_no,
			use_serial_batch_fields=1,
			posting_date=add_days(today(), -3),
			posting_time="12:00:00",
		)

		issue = make_stock_entry(
			item_code=item_code,
			qty=2,
			source=warehouse,
			posting_date=add_days(today(), -3),
			posting_time="12:00:00",
			do_not_save=True,
		)

		for qty in [3, 4]:
			issue.append(
				"items",
				{
					"item_code": item_code,
					"s_warehouse": warehouse,
					"qty": qty,
					"conversion_factor": 1,
				},
			)

		issue.save()
		issue.submit()

		# (10 * 100 + 20 * 250) / 30 = 200
		self.assert_batchwise_outgoing_rate(item_code, outgoing_rate=200.0, balance_value=4200.0)

		# backdated receipt reposts the same posting datetime cluster
		make_stock_entry(
			item_code=item_code,
			qty=10,
			rate=100,
			target=warehouse,
			batch_no=batch_no,
			use_serial_batch_fields=1,
			posting_date=add_days(today(), -4),
			posting_time="12:00:00",
		)

		# (20 * 100 + 20 * 250) / 40 = 175
		self.assert_batchwise_outgoing_rate(item_code, outgoing_rate=175.0, balance_value=5425.0)

	@ERPNextTestSuite.change_settings(
		"Stock Settings", {"auto_create_serial_and_batch_bundle_for_outward": 1}
	)
	def test_batchwise_valuation_when_bundle_created_before_the_sle(self):
		# a bundle can be created (drafted) much before / after its SLE, the
		# tie-breaking for the same posting datetime entries must follow the
		# SLE creation and not the bundle creation
		item_code = make_item(
			"Test Batchwise Same Posting Datetime Item 2",
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "TBSPD-ITEM2-.#####",
				"valuation_method": "FIFO",
			},
		).name

		warehouse = "_Test Warehouse - _TC"

		receipt = make_stock_entry(
			item_code=item_code,
			qty=10,
			rate=100,
			target=warehouse,
			posting_date=add_days(today(), -5),
			posting_time="12:00:00",
		)

		batch_no = get_batch_from_bundle(receipt.items[0].serial_and_batch_bundle)

		# inward at a different rate, same posting datetime as the outward below
		inward = make_stock_entry(
			item_code=item_code,
			qty=10,
			rate=200,
			target=warehouse,
			batch_no=batch_no,
			use_serial_batch_fields=1,
			posting_date=add_days(today(), -3),
			posting_time="12:00:00",
		)

		outward = make_stock_entry(
			item_code=item_code,
			qty=10,
			source=warehouse,
			posting_date=add_days(today(), -3),
			posting_time="12:00:00",
		)

		# simulate the inward's bundle drafted after the outward's SLE, the
		# bundle creation timeline no longer matches the SLE creation timeline
		outward_sle_creation = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_no": outward.name, "is_cancelled": 0},
			"creation",
		)

		frappe.db.set_value(
			"Serial and Batch Bundle",
			inward.items[0].serial_and_batch_bundle,
			"creation",
			add_to_date(outward_sle_creation, minutes=30),
			update_modified=False,
		)

		repost = frappe.get_doc(
			{
				"doctype": "Repost Item Valuation",
				"based_on": "Item and Warehouse",
				"item_code": item_code,
				"warehouse": warehouse,
				"posting_date": add_days(today(), -6),
				"posting_time": "00:00:00",
				"allow_negative_stock": 1,
			}
		)

		repost.submit()

		# (10 * 100 + 10 * 200) / 20 = 150, the inward precedes the outward as
		# per the SLE creation even though its bundle was created afterwards
		self.assert_batchwise_outgoing_rate(item_code, outgoing_rate=150.0, balance_value=1500.0)

	def assert_batchwise_outgoing_rate(self, item_code, outgoing_rate, balance_value):
		sl_entries = frappe.get_all(
			"Stock Ledger Entry",
			filters={"item_code": item_code, "is_cancelled": 0},
			fields=["actual_qty", "stock_value_difference", "stock_value"],
			order_by="posting_datetime, creation",
		)

		for sle in sl_entries:
			if sle.actual_qty > 0:
				continue

			self.assertEqual(flt(sle.stock_value_difference, 2), flt(sle.actual_qty * outgoing_rate, 2))

		self.assertEqual(flt(sl_entries[-1].stock_value, 2), flt(balance_value, 2))
