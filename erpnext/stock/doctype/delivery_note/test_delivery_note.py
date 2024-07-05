# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, cstr, flt, nowdate, nowtime, today

from erpnext.accounts.doctype.account.test_account import get_inventory_account
from erpnext.accounts.utils import get_balance_on
from erpnext.selling.doctype.product_bundle.test_product_bundle import make_product_bundle
from erpnext.selling.doctype.sales_order.test_sales_order import (
	automatically_fetch_payment_terms,
	compare_payment_schedules,
	create_dn_against_so,
	make_sales_order,
)
from erpnext.stock.doctype.delivery_note.delivery_note import (
	make_delivery_trip,
	make_sales_invoice,
)
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import get_gl_entries
from erpnext.stock.doctype.serial_and_batch_bundle.test_serial_and_batch_bundle import (
	get_batch_from_bundle,
	get_serial_nos_from_bundle,
	make_serial_batch_bundle,
)
from erpnext.stock.doctype.stock_entry.test_stock_entry import (
	get_qty_after_transaction,
	make_serialized_item,
	make_stock_entry,
)
from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
	create_stock_reconciliation,
	set_valuation_method,
)
from erpnext.stock.doctype.warehouse.test_warehouse import get_warehouse
from erpnext.stock.stock_ledger import get_previous_sle


class TestDeliveryNote(FrappeTestCase):
	def test_over_billing_against_dn(self):
		frappe.db.set_single_value("Stock Settings", "allow_negative_stock", 1)

		dn = create_delivery_note(do_not_submit=True)
		self.assertRaises(frappe.ValidationError, make_sales_invoice, dn.name)

		dn.submit()
		si = make_sales_invoice(dn.name)
		self.assertEqual(len(si.get("items")), len(dn.get("items")))

		# modify amount
		si.get("items")[0].rate = 200
		self.assertRaises(frappe.ValidationError, frappe.get_doc(si).insert)

	def test_delivery_note_no_gl_entry(self):
		frappe.db.get_value("Warehouse", "_Test Warehouse - _TC", "company")
		make_stock_entry(target="_Test Warehouse - _TC", qty=5, basic_rate=100)

		stock_queue = json.loads(
			get_previous_sle(
				{
					"item_code": "_Test Item",
					"warehouse": "_Test Warehouse - _TC",
					"posting_date": nowdate(),
					"posting_time": nowtime(),
				}
			).stock_queue
			or "[]"
		)

		dn = create_delivery_note()

		sle = frappe.get_doc("Stock Ledger Entry", {"voucher_type": "Delivery Note", "voucher_no": dn.name})

		self.assertEqual(sle.stock_value_difference, flt(-1 * stock_queue[0][1], 2))

		self.assertFalse(get_gl_entries("Delivery Note", dn.name))

	def test_delivery_note_gl_entry_packing_item(self):
		frappe.db.get_value("Warehouse", "Stores - TCP1", "company")

		make_stock_entry(item_code="_Test Item", target="Stores - TCP1", qty=10, basic_rate=100)
		make_stock_entry(
			item_code="_Test Item Home Desktop 100", target="Stores - TCP1", qty=10, basic_rate=100
		)

		stock_in_hand_account = get_inventory_account("_Test Company with perpetual inventory")
		prev_bal = get_balance_on(stock_in_hand_account)

		dn = create_delivery_note(
			item_code="_Test Product Bundle Item",
			company="_Test Company with perpetual inventory",
			warehouse="Stores - TCP1",
			cost_center="Main - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
		)

		stock_value_diff_rm1 = abs(
			frappe.db.get_value(
				"Stock Ledger Entry",
				{"voucher_type": "Delivery Note", "voucher_no": dn.name, "item_code": "_Test Item"},
				"stock_value_difference",
			)
		)

		stock_value_diff_rm2 = abs(
			frappe.db.get_value(
				"Stock Ledger Entry",
				{
					"voucher_type": "Delivery Note",
					"voucher_no": dn.name,
					"item_code": "_Test Item Home Desktop 100",
				},
				"stock_value_difference",
			)
		)

		stock_value_diff = stock_value_diff_rm1 + stock_value_diff_rm2

		gl_entries = get_gl_entries("Delivery Note", dn.name)
		self.assertTrue(gl_entries)

		expected_values = {
			stock_in_hand_account: [0.0, stock_value_diff],
			"Cost of Goods Sold - TCP1": [stock_value_diff, 0.0],
		}
		for _i, gle in enumerate(gl_entries):
			self.assertEqual([gle.debit, gle.credit], expected_values.get(gle.account))

		# check stock in hand balance
		bal = get_balance_on(stock_in_hand_account)
		self.assertEqual(flt(bal, 2), flt(prev_bal - stock_value_diff, 2))

		dn.cancel()

	def test_serialize_status(self):
		from frappe.model.naming import make_autoname

		serial_no = frappe.get_doc(
			{
				"doctype": "Serial No",
				"item_code": "_Test Serialized Item With Series",
				"serial_no": make_autoname("SRDD", "Serial No"),
			}
		)
		serial_no.save()

		bundle_id = make_serial_batch_bundle(
			frappe._dict(
				{
					"item_code": "_Test Serialized Item With Series",
					"warehouse": "_Test Warehouse - _TC",
					"qty": -1,
					"voucher_type": "Delivery Note",
					"serial_nos": [serial_no.name],
					"posting_date": today(),
					"posting_time": nowtime(),
					"type_of_transaction": "Outward",
					"do_not_save": True,
				}
			)
		)

		self.assertRaises(frappe.ValidationError, bundle_id.make_serial_and_batch_bundle)

	def check_serial_no_values(self, serial_no, field_values):
		serial_no = frappe.get_doc("Serial No", serial_no)
		for field, value in field_values.items():
			self.assertEqual(cstr(serial_no.get(field)), value)

	def test_delivery_note_return_against_denormalized_serial_no(self):
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_return
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		frappe.flags.ignore_serial_batch_bundle_validation = True
		sn_item = "Old Serial NO Item Return Test - 1"
		make_item(
			sn_item,
			{
				"has_serial_no": 1,
				"serial_no_series": "OSN-.####",
				"is_stock_item": 1,
			},
		)

		serial_nos = [
			"OSN-1",
			"OSN-2",
			"OSN-3",
			"OSN-4",
			"OSN-5",
			"OSN-6",
			"OSN-7",
			"OSN-8",
			"OSN-9",
			"OSN-10",
			"OSN-11",
			"OSN-12",
		]

		for sn in serial_nos:
			if not frappe.db.exists("Serial No", sn):
				sn_doc = frappe.get_doc(
					{
						"doctype": "Serial No",
						"item_code": sn_item,
						"serial_no": sn,
					}
				)
				sn_doc.insert()

		warehouse = "_Test Warehouse - _TC"
		company = frappe.db.get_value("Warehouse", warehouse, "company")
		se_doc = make_stock_entry(
			item_code=sn_item,
			company=company,
			target="_Test Warehouse - _TC",
			qty=12,
			basic_rate=100,
			do_not_submit=1,
		)

		se_doc.items[0].serial_no = "\n".join(serial_nos)

		frappe.flags.use_serial_and_batch_fields = True
		se_doc.submit()

		self.assertEqual(sorted(get_serial_nos(se_doc.items[0].serial_no)), sorted(serial_nos))

		dn = create_delivery_note(
			item_code=sn_item,
			qty=12,
			rate=500,
			warehouse=warehouse,
			company=company,
			expense_account="Cost of Goods Sold - _TC",
			cost_center="Main - _TC",
			do_not_submit=1,
		)

		dn.items[0].serial_no = "\n".join(serial_nos)
		dn.submit()
		dn.reload()

		self.assertTrue(dn.items[0].serial_no)

		frappe.flags.ignore_serial_batch_bundle_validation = False
		frappe.flags.use_serial_and_batch_fields = False

		# return entry
		dn1 = make_sales_return(dn.name)

		dn1.items[0].qty = -2
		dn1.items[0].serial_no = "\n".join(get_serial_nos(serial_nos)[0:2])
		dn1.submit()
		dn1.reload()

		returned_serial_nos1 = get_serial_nos_from_bundle(dn1.items[0].serial_and_batch_bundle)
		for serial_no in returned_serial_nos1:
			self.assertTrue(serial_no in serial_nos)

		dn2 = make_sales_return(dn.name)

		dn2.items[0].qty = -2
		dn2.items[0].serial_no = "\n".join(get_serial_nos(serial_nos)[2:4])
		dn2.submit()
		dn2.reload()

		returned_serial_nos2 = get_serial_nos_from_bundle(dn2.items[0].serial_and_batch_bundle)
		for serial_no in returned_serial_nos2:
			self.assertTrue(serial_no in serial_nos)
			self.assertFalse(serial_no in returned_serial_nos1)

	def test_sales_return_for_non_bundled_items_partial(self):
		company = frappe.db.get_value("Warehouse", "Stores - TCP1", "company")

		make_stock_entry(item_code="_Test Item", target="Stores - TCP1", qty=50, basic_rate=100)

		actual_qty_0 = get_qty_after_transaction(warehouse="Stores - TCP1")

		dn = create_delivery_note(
			qty=5,
			rate=500,
			warehouse="Stores - TCP1",
			company=company,
			expense_account="Cost of Goods Sold - TCP1",
			cost_center="Main - TCP1",
		)

		actual_qty_1 = get_qty_after_transaction(warehouse="Stores - TCP1")
		self.assertEqual(actual_qty_0 - 5, actual_qty_1)

		# outgoing_rate
		outgoing_rate = (
			frappe.db.get_value(
				"Stock Ledger Entry",
				{"voucher_type": "Delivery Note", "voucher_no": dn.name},
				"stock_value_difference",
			)
			/ 5
		)

		# return entry
		dn1 = create_delivery_note(
			is_return=1,
			return_against=dn.name,
			qty=-2,
			rate=500,
			company=company,
			warehouse="Stores - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			cost_center="Main - TCP1",
			do_not_submit=1,
		)
		dn1.items[0].dn_detail = dn.items[0].name
		dn1.submit()

		actual_qty_2 = get_qty_after_transaction(warehouse="Stores - TCP1")

		self.assertEqual(actual_qty_1 + 2, actual_qty_2)

		incoming_rate, stock_value_difference = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": "Delivery Note", "voucher_no": dn1.name},
			["incoming_rate", "stock_value_difference"],
		)

		self.assertEqual(flt(incoming_rate, 3), abs(flt(outgoing_rate, 3)))
		stock_in_hand_account = get_inventory_account(company, dn1.items[0].warehouse)

		gle_warehouse_amount = frappe.db.get_value(
			"GL Entry",
			{"voucher_type": "Delivery Note", "voucher_no": dn1.name, "account": stock_in_hand_account},
			"debit",
		)

		self.assertEqual(gle_warehouse_amount, stock_value_difference)

		# hack because new_doc isn't considering is_return portion of status_updater
		returned = frappe.get_doc("Delivery Note", dn1.name)
		returned.update_prevdoc_status()
		dn.load_from_db()

		# Check if Original DN updated
		self.assertEqual(dn.items[0].returned_qty, 2)
		self.assertEqual(dn.per_returned, 40)

		from erpnext.controllers.sales_and_purchase_return import make_return_doc

		return_dn_2 = make_return_doc("Delivery Note", dn.name)

		# Check if unreturned amount is mapped in 2nd return
		self.assertEqual(return_dn_2.items[0].qty, -3)

		si = make_sales_invoice(dn.name)
		si.submit()

		self.assertEqual(si.items[0].qty, 3)

		dn.load_from_db()
		# DN should be completed on billing all unreturned amount
		self.assertEqual(dn.items[0].billed_amt, 1500)
		self.assertEqual(dn.per_billed, 100)
		self.assertEqual(dn.status, "Completed")

		si.load_from_db()
		si.cancel()

		dn.load_from_db()
		self.assertEqual(dn.per_billed, 0)

		dn1.cancel()
		dn.cancel()

	def test_sales_return_for_non_bundled_items_full(self):
		company = frappe.db.get_value("Warehouse", "Stores - TCP1", "company")

		make_item("Box", {"is_stock_item": 1})

		make_stock_entry(item_code="Box", target="Stores - TCP1", qty=10, basic_rate=100)

		dn = create_delivery_note(
			item_code="Box",
			qty=5,
			rate=500,
			warehouse="Stores - TCP1",
			company=company,
			expense_account="Cost of Goods Sold - TCP1",
			cost_center="Main - TCP1",
		)

		# return entry
		dn1 = create_delivery_note(
			item_code="Box",
			is_return=1,
			return_against=dn.name,
			qty=-5,
			rate=500,
			company=company,
			warehouse="Stores - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			cost_center="Main - TCP1",
			do_not_submit=1,
		)
		dn1.items[0].dn_detail = dn.items[0].name
		dn1.submit()

		# hack because new_doc isn't considering is_return portion of status_updater
		returned = frappe.get_doc("Delivery Note", dn1.name)
		returned.update_prevdoc_status()
		dn.load_from_db()

		# Check if Original DN updated
		self.assertEqual(dn.items[0].returned_qty, 5)
		self.assertEqual(dn.per_returned, 100)
		self.assertEqual(dn.status, "Return Issued")

	def test_delivery_note_return_valuation_on_different_warehouse(self):
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		company = frappe.db.get_value("Warehouse", "Stores - TCP1", "company")
		item_code = "Test Return Valuation For DN"
		make_item("Test Return Valuation For DN", {"is_stock_item": 1})
		return_warehouse = create_warehouse("Returned Test Warehouse", company=company)

		make_stock_entry(item_code=item_code, target="Stores - TCP1", qty=5, basic_rate=150)

		dn = create_delivery_note(
			item_code=item_code,
			qty=5,
			rate=500,
			warehouse="Stores - TCP1",
			company=company,
			expense_account="Cost of Goods Sold - TCP1",
			cost_center="Main - TCP1",
		)

		dn.submit()
		self.assertEqual(dn.items[0].incoming_rate, 150)

		from erpnext.controllers.sales_and_purchase_return import make_return_doc

		return_dn = make_return_doc(dn.doctype, dn.name)
		return_dn.items[0].warehouse = return_warehouse
		return_dn.save().submit()

		self.assertEqual(return_dn.items[0].incoming_rate, 150)

	def test_sales_return_against_serial_batch_bundle(self):
		frappe.db.set_single_value(
			"Stock Settings", "do_not_update_serial_batch_on_creation_of_auto_bundle", 1
		)

		batch_item = make_item(
			"Test Sales Return Against Batch Item",
			properties={
				"has_batch_no": 1,
				"is_stock_item": 1,
				"create_new_batch": 1,
				"batch_number_series": "BATCH-TSRABII.#####",
			},
		).name

		serial_item = make_item(
			"Test Sales Return Against Serial NO Item",
			properties={
				"has_serial_no": 1,
				"is_stock_item": 1,
				"serial_no_series": "SN-TSRABII.#####",
			},
		).name

		make_stock_entry(item_code=batch_item, target="_Test Warehouse - _TC", qty=5, basic_rate=100)
		make_stock_entry(item_code=serial_item, target="_Test Warehouse - _TC", qty=5, basic_rate=100)

		dn = create_delivery_note(
			item_code=batch_item,
			qty=5,
			rate=500,
			warehouse="_Test Warehouse - _TC",
			expense_account="Cost of Goods Sold - _TC",
			cost_center="Main - _TC",
			use_serial_batch_fields=0,
			do_not_submit=1,
		)

		dn.append(
			"items",
			{
				"item_code": serial_item,
				"qty": 5,
				"rate": 500,
				"warehouse": "_Test Warehouse - _TC",
				"expense_account": "Cost of Goods Sold - _TC",
				"cost_center": "Main - _TC",
				"use_serial_batch_fields": 0,
			},
		)

		dn.save()
		for row in dn.items:
			self.assertFalse(row.use_serial_batch_fields)

		dn.submit()
		dn.reload()
		for row in dn.items:
			self.assertTrue(row.serial_and_batch_bundle)
			self.assertFalse(row.use_serial_batch_fields)
			self.assertFalse(row.serial_no)
			self.assertFalse(row.batch_no)

		from erpnext.controllers.sales_and_purchase_return import make_return_doc

		return_dn = make_return_doc(dn.doctype, dn.name)
		for row in return_dn.items:
			row.qty = -2
			row.use_serial_batch_fields = 0
		return_dn.save().submit()

		for row in return_dn.items:
			total_qty = frappe.db.get_value(
				"Serial and Batch Bundle", row.serial_and_batch_bundle, "total_qty"
			)

			self.assertEqual(total_qty, 2)

			doc = frappe.get_doc("Serial and Batch Bundle", row.serial_and_batch_bundle)
			if doc.has_serial_no:
				self.assertEqual(len(doc.entries), 2)

			for entry in doc.entries:
				if doc.has_batch_no:
					self.assertEqual(entry.qty, 2)
				else:
					self.assertEqual(entry.qty, 1)

		frappe.db.set_single_value(
			"Stock Settings", "do_not_update_serial_batch_on_creation_of_auto_bundle", 0
		)

	def test_return_single_item_from_bundled_items(self):
		company = frappe.db.get_value("Warehouse", "Stores - TCP1", "company")

		create_stock_reconciliation(
			item_code="_Test Item",
			warehouse="Stores - TCP1",
			qty=50,
			rate=100,
			company=company,
			expense_account="Stock Adjustment - TCP1",
		)
		create_stock_reconciliation(
			item_code="_Test Item Home Desktop 100",
			warehouse="Stores - TCP1",
			qty=50,
			rate=100,
			company=company,
			expense_account="Stock Adjustment - TCP1",
		)

		dn = create_delivery_note(
			item_code="_Test Product Bundle Item",
			qty=5,
			rate=500,
			company=company,
			warehouse="Stores - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			cost_center="Main - TCP1",
		)

		# Qty after delivery
		actual_qty_1 = get_qty_after_transaction(warehouse="Stores - TCP1")
		self.assertEqual(actual_qty_1, 25)

		# outgoing_rate
		outgoing_rate = (
			frappe.db.get_value(
				"Stock Ledger Entry",
				{"voucher_type": "Delivery Note", "voucher_no": dn.name, "item_code": "_Test Item"},
				"stock_value_difference",
			)
			/ 25
		)

		# return 'test item' from packed items
		dn1 = create_delivery_note(
			is_return=1,
			return_against=dn.name,
			qty=-10,
			rate=500,
			company=company,
			warehouse="Stores - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			cost_center="Main - TCP1",
		)

		# qty after return
		actual_qty_2 = get_qty_after_transaction(warehouse="Stores - TCP1")
		self.assertEqual(actual_qty_2, 35)

		# Check incoming rate for return entry
		incoming_rate, stock_value_difference = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": "Delivery Note", "voucher_no": dn1.name},
			["incoming_rate", "stock_value_difference"],
		)

		self.assertEqual(flt(incoming_rate, 3), abs(flt(outgoing_rate, 3)))
		stock_in_hand_account = get_inventory_account(company, dn1.items[0].warehouse)

		# Check gl entry for warehouse
		gle_warehouse_amount = frappe.db.get_value(
			"GL Entry",
			{"voucher_type": "Delivery Note", "voucher_no": dn1.name, "account": stock_in_hand_account},
			"debit",
		)

		self.assertEqual(gle_warehouse_amount, stock_value_difference)

	def test_return_entire_bundled_items(self):
		company = frappe.db.get_value("Warehouse", "Stores - TCP1", "company")

		create_stock_reconciliation(
			item_code="_Test Item",
			warehouse="Stores - TCP1",
			qty=50,
			rate=100,
			company=company,
			expense_account="Stock Adjustment - TCP1",
		)
		create_stock_reconciliation(
			item_code="_Test Item Home Desktop 100",
			warehouse="Stores - TCP1",
			qty=50,
			rate=100,
			company=company,
			expense_account="Stock Adjustment - TCP1",
		)

		actual_qty = get_qty_after_transaction(warehouse="Stores - TCP1")
		self.assertEqual(actual_qty, 50)

		dn = create_delivery_note(
			item_code="_Test Product Bundle Item",
			qty=5,
			rate=500,
			company=company,
			warehouse="Stores - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			cost_center="Main - TCP1",
		)

		# qty after return
		actual_qty = get_qty_after_transaction(warehouse="Stores - TCP1")
		self.assertEqual(actual_qty, 25)

		#  return bundled item
		dn1 = create_delivery_note(
			item_code="_Test Product Bundle Item",
			is_return=1,
			return_against=dn.name,
			qty=-2,
			rate=500,
			company=company,
			warehouse="Stores - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			cost_center="Main - TCP1",
		)

		# qty after return
		actual_qty = get_qty_after_transaction(warehouse="Stores - TCP1")
		self.assertEqual(actual_qty, 35)

		# Check incoming rate for return entry
		incoming_rate, stock_value_difference = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": "Delivery Note", "voucher_no": dn1.name},
			["incoming_rate", "stock_value_difference"],
		)

		self.assertEqual(incoming_rate, 100)
		stock_in_hand_account = get_inventory_account("_Test Company", dn1.items[0].warehouse)

		# Check gl entry for warehouse
		gle_warehouse_amount = frappe.db.get_value(
			"GL Entry",
			{"voucher_type": "Delivery Note", "voucher_no": dn1.name, "account": stock_in_hand_account},
			"debit",
		)

		self.assertEqual(gle_warehouse_amount, 1400)

	def test_bin_details_of_packed_item(self):
		from erpnext.selling.doctype.product_bundle.test_product_bundle import make_product_bundle
		from erpnext.stock.doctype.item.test_item import make_item

		# test Update Items with product bundle
		if not frappe.db.exists("Item", "_Test Product Bundle Item New"):
			bundle_item = make_item("_Test Product Bundle Item New", {"is_stock_item": 0})
			bundle_item.append(
				"item_defaults", {"company": "_Test Company", "default_warehouse": "_Test Warehouse - _TC"}
			)
			bundle_item.save(ignore_permissions=True)

		make_item("_Packed Item New 1", {"is_stock_item": 1})
		make_product_bundle("_Test Product Bundle Item New", ["_Packed Item New 1"], 2)

		si = create_delivery_note(
			item_code="_Test Product Bundle Item New",
			update_stock=1,
			warehouse="_Test Warehouse - _TC",
			transaction_date=add_days(nowdate(), -1),
			do_not_submit=1,
		)

		make_stock_entry(item="_Packed Item New 1", target="_Test Warehouse - _TC", qty=120, rate=100)

		bin_details = frappe.db.get_value(
			"Bin",
			{"item_code": "_Packed Item New 1", "warehouse": "_Test Warehouse - _TC"},
			["actual_qty", "projected_qty", "ordered_qty"],
			as_dict=1,
		)

		si.transaction_date = nowdate()
		si.save()

		packed_item = si.packed_items[0]
		self.assertEqual(flt(bin_details.actual_qty), flt(packed_item.actual_qty))
		self.assertEqual(flt(bin_details.projected_qty), flt(packed_item.projected_qty))
		self.assertEqual(flt(bin_details.ordered_qty), flt(packed_item.ordered_qty))

	def test_return_for_serialized_items(self):
		se = make_serialized_item()

		serial_no = [get_serial_nos_from_bundle(se.get("items")[0].serial_and_batch_bundle)[0]]

		dn = create_delivery_note(
			item_code="_Test Serialized Item With Series", rate=500, serial_no=serial_no
		)

		self.check_serial_no_values(serial_no, {"warehouse": ""})

		# return entry
		dn1 = create_delivery_note(
			item_code="_Test Serialized Item With Series",
			is_return=1,
			return_against=dn.name,
			qty=-1,
			rate=500,
			serial_no=serial_no,
		)

		self.check_serial_no_values(serial_no, {"warehouse": "_Test Warehouse - _TC"})

		dn1.cancel()

		self.check_serial_no_values(serial_no, {"warehouse": ""})

		dn.cancel()

		self.check_serial_no_values(
			serial_no,
			{"warehouse": "_Test Warehouse - _TC"},
		)

	def test_delivery_of_bundled_items_to_target_warehouse(self):
		from erpnext.selling.doctype.customer.test_customer import create_internal_customer

		company = frappe.db.get_value("Warehouse", "Stores - TCP1", "company")
		customer_name = create_internal_customer(
			customer_name="_Test Internal Customer 2",
			represents_company="_Test Company with perpetual inventory",
			allowed_to_interact_with="_Test Company with perpetual inventory",
		)

		set_valuation_method("_Test Item", "FIFO")
		set_valuation_method("_Test Item Home Desktop 100", "FIFO")

		target_warehouse = get_warehouse(
			company=company, abbr="TCP1", warehouse_name="_Test Customer Warehouse"
		).name

		for warehouse in ("Stores - TCP1", target_warehouse):
			create_stock_reconciliation(
				item_code="_Test Item",
				warehouse=warehouse,
				company=company,
				expense_account="Stock Adjustment - TCP1",
				qty=500,
				rate=100,
			)
			create_stock_reconciliation(
				item_code="_Test Item Home Desktop 100",
				company=company,
				expense_account="Stock Adjustment - TCP1",
				warehouse=warehouse,
				qty=500,
				rate=100,
			)

		dn = create_delivery_note(
			item_code="_Test Product Bundle Item",
			company="_Test Company with perpetual inventory",
			customer=customer_name,
			cost_center="Main - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			qty=5,
			rate=500,
			warehouse="Stores - TCP1",
			target_warehouse=target_warehouse,
		)

		# qty after delivery
		actual_qty_at_source = get_qty_after_transaction(warehouse="Stores - TCP1")
		self.assertEqual(actual_qty_at_source, 475)

		actual_qty_at_target = get_qty_after_transaction(warehouse=target_warehouse)
		self.assertEqual(actual_qty_at_target, 525)

		# stock value diff for source warehouse for "_Test Item"
		stock_value_difference = frappe.db.get_value(
			"Stock Ledger Entry",
			{
				"voucher_type": "Delivery Note",
				"voucher_no": dn.name,
				"item_code": "_Test Item",
				"warehouse": "Stores - TCP1",
			},
			"stock_value_difference",
		)

		# stock value diff for target warehouse
		stock_value_difference1 = frappe.db.get_value(
			"Stock Ledger Entry",
			{
				"voucher_type": "Delivery Note",
				"voucher_no": dn.name,
				"item_code": "_Test Item",
				"warehouse": target_warehouse,
			},
			"stock_value_difference",
		)

		self.assertEqual(abs(stock_value_difference), stock_value_difference1)

		# Check gl entries
		gl_entries = get_gl_entries("Delivery Note", dn.name)
		self.assertTrue(gl_entries)

		stock_value_difference = abs(
			frappe.db.sql(
				"""select sum(stock_value_difference)
			from `tabStock Ledger Entry` where voucher_type='Delivery Note' and voucher_no=%s
			and warehouse='Stores - TCP1'""",
				dn.name,
			)[0][0]
		)

		expected_values = {
			"Stock In Hand - TCP1": [0.0, stock_value_difference],
			target_warehouse: [stock_value_difference, 0.0],
		}
		for _i, gle in enumerate(gl_entries):
			self.assertEqual([gle.debit, gle.credit], expected_values.get(gle.account))

		# tear down
		frappe.db.rollback()

	def test_closed_delivery_note(self):
		from erpnext.stock.doctype.delivery_note.delivery_note import update_delivery_note_status

		make_stock_entry(target="Stores - TCP1", qty=5, basic_rate=100)

		dn = create_delivery_note(
			company="_Test Company with perpetual inventory",
			warehouse="Stores - TCP1",
			cost_center="Main - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			do_not_submit=True,
		)

		dn.submit()

		update_delivery_note_status(dn.name, "Closed")
		self.assertEqual(frappe.db.get_value("Delivery Note", dn.name, "Status"), "Closed")

		# Check cancelling closed delivery note
		dn.load_from_db()
		dn.cancel()
		self.assertEqual(dn.status, "Cancelled")

	def test_sales_order_reference_validation(self):
		so = make_sales_order(po_no="12345")
		dn = create_dn_against_so(so.name, delivered_qty=2, do_not_submit=True)
		dn.items[0].against_sales_order = None
		self.assertRaises(frappe.ValidationError, dn.save)
		dn.reload()
		dn.items[0].so_detail = None
		self.assertRaises(frappe.ValidationError, dn.save)

	def test_dn_billing_status_case1(self):
		# SO -> DN -> SI
		so = make_sales_order(po_no="12345")
		dn = create_dn_against_so(so.name, delivered_qty=2)

		self.assertEqual(dn.status, "To Bill")
		self.assertEqual(dn.per_billed, 0)

		# Testing if Customer's Purchase Order No was rightly copied
		self.assertEqual(dn.po_no, so.po_no)

		si = make_sales_invoice(dn.name)
		si.submit()

		# Testing if Customer's Purchase Order No was rightly copied
		self.assertEqual(dn.po_no, si.po_no)

		dn.load_from_db()
		self.assertEqual(dn.get("items")[0].billed_amt, 200)
		self.assertEqual(dn.per_billed, 100)
		self.assertEqual(dn.status, "Completed")

	def test_dn_billing_status_case2(self):
		# SO -> SI and SO -> DN1, DN2
		from erpnext.selling.doctype.sales_order.sales_order import (
			make_delivery_note,
			make_sales_invoice,
		)

		so = make_sales_order(po_no="12345")

		si = make_sales_invoice(so.name)
		si.get("items")[0].qty = 5
		si.insert()
		si.submit()

		# Testing if Customer's Purchase Order No was rightly copied
		self.assertEqual(so.po_no, si.po_no)

		frappe.db.set_single_value("Stock Settings", "allow_negative_stock", 1)

		dn1 = make_delivery_note(so.name)
		dn1.get("items")[0].qty = 2
		dn1.submit()

		# Testing if Customer's Purchase Order No was rightly copied
		self.assertEqual(so.po_no, dn1.po_no)

		dn2 = make_delivery_note(so.name)
		dn2.get("items")[0].qty = 3
		dn2.submit()

		# Testing if Customer's Purchase Order No was rightly copied
		self.assertEqual(so.po_no, dn2.po_no)

		dn1.load_from_db()
		self.assertEqual(dn1.get("items")[0].billed_amt, 200)
		self.assertEqual(dn1.per_billed, 100)
		self.assertEqual(dn1.status, "Completed")

		self.assertEqual(dn2.get("items")[0].billed_amt, 300)
		self.assertEqual(dn2.per_billed, 100)
		self.assertEqual(dn2.status, "Completed")

	def test_dn_billing_status_case3(self):
		# SO -> DN1 -> SI and SO -> SI and SO -> DN2
		from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
		from erpnext.selling.doctype.sales_order.sales_order import (
			make_sales_invoice as make_sales_invoice_from_so,
		)

		frappe.db.set_single_value("Stock Settings", "allow_negative_stock", 1)

		so = make_sales_order(po_no="12345")

		dn1 = make_delivery_note(so.name)
		dn1.get("items")[0].qty = 2
		dn1.submit()

		# Testing if Customer's Purchase Order No was rightly copied
		self.assertEqual(dn1.po_no, so.po_no)

		si1 = make_sales_invoice(dn1.name)
		si1.submit()

		# Testing if Customer's Purchase Order No was rightly copied
		self.assertEqual(dn1.po_no, si1.po_no)

		dn1.load_from_db()
		self.assertEqual(dn1.per_billed, 100)

		si2 = make_sales_invoice_from_so(so.name)
		si2.get("items")[0].qty = 4
		si2.submit()

		# Testing if Customer's Purchase Order No was rightly copied
		self.assertEqual(si2.po_no, so.po_no)

		dn2 = make_delivery_note(so.name)
		dn2.get("items")[0].qty = 5
		dn2.submit()

		# Testing if Customer's Purchase Order No was rightly copied
		self.assertEqual(dn2.po_no, so.po_no)

		dn1.load_from_db()
		self.assertEqual(dn1.get("items")[0].billed_amt, 200)
		self.assertEqual(dn1.per_billed, 100)
		self.assertEqual(dn1.status, "Completed")

		self.assertEqual(dn2.get("items")[0].billed_amt, 400)
		self.assertEqual(dn2.per_billed, 80)
		self.assertEqual(dn2.status, "To Bill")

	def test_dn_billing_status_case4(self):
		# SO -> SI -> DN
		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_delivery_note
		from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice

		so = make_sales_order(po_no="12345")

		si = make_sales_invoice(so.name)
		si.submit()

		# Testing if Customer's Purchase Order No was rightly copied
		self.assertEqual(so.po_no, si.po_no)

		dn = make_delivery_note(si.name)
		dn.submit()

		# Testing if Customer's Purchase Order No was rightly copied
		self.assertEqual(dn.po_no, si.po_no)

		self.assertEqual(dn.get("items")[0].billed_amt, 1000)
		self.assertEqual(dn.per_billed, 100)
		self.assertEqual(dn.status, "Completed")

	def test_delivery_trip(self):
		dn = create_delivery_note()
		dt = make_delivery_trip(dn.name)
		self.assertEqual(dn.name, dt.delivery_stops[0].delivery_note)

	def test_delivery_note_with_cost_center(self):
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center

		cost_center = "_Test Cost Center for BS Account - TCP1"
		create_cost_center(
			cost_center_name="_Test Cost Center for BS Account",
			company="_Test Company with perpetual inventory",
		)

		set_valuation_method("_Test Item", "FIFO")

		make_stock_entry(target="Stores - TCP1", qty=5, basic_rate=100)

		stock_in_hand_account = get_inventory_account("_Test Company with perpetual inventory")
		dn = create_delivery_note(
			company="_Test Company with perpetual inventory",
			warehouse="Stores - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			cost_center=cost_center,
		)

		gl_entries = get_gl_entries("Delivery Note", dn.name)
		self.assertTrue(gl_entries)

		expected_values = {
			"Cost of Goods Sold - TCP1": {"cost_center": cost_center},
			stock_in_hand_account: {"cost_center": cost_center},
		}
		for _i, gle in enumerate(gl_entries):
			self.assertEqual(expected_values[gle.account]["cost_center"], gle.cost_center)

	def test_delivery_note_cost_center_with_balance_sheet_account(self):
		cost_center = "Main - TCP1"

		set_valuation_method("_Test Item", "FIFO")

		make_stock_entry(target="Stores - TCP1", qty=5, basic_rate=100)

		stock_in_hand_account = get_inventory_account("_Test Company with perpetual inventory")
		dn = create_delivery_note(
			company="_Test Company with perpetual inventory",
			warehouse="Stores - TCP1",
			cost_center="Main - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			do_not_submit=1,
		)

		dn.get("items")[0].cost_center = None
		dn.submit()

		gl_entries = get_gl_entries("Delivery Note", dn.name)

		self.assertTrue(gl_entries)
		expected_values = {
			"Cost of Goods Sold - TCP1": {"cost_center": cost_center},
			stock_in_hand_account: {"cost_center": cost_center},
		}
		for _i, gle in enumerate(gl_entries):
			self.assertEqual(expected_values[gle.account]["cost_center"], gle.cost_center)

	def test_make_sales_invoice_from_dn_for_returned_qty(self):
		from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		so = make_sales_order(qty=2)
		so.submit()

		dn = make_delivery_note(so.name)
		dn.submit()

		dn1 = create_delivery_note(is_return=1, return_against=dn.name, qty=-1, do_not_submit=True)
		dn1.items[0].against_sales_order = so.name
		dn1.items[0].so_detail = so.items[0].name
		dn1.items[0].dn_detail = dn.items[0].name
		dn1.submit()

		si = make_sales_invoice(dn.name)
		self.assertEqual(si.items[0].qty, 1)

	def test_make_sales_invoice_from_dn_with_returned_qty_duplicate_items(self):
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		dn = create_delivery_note(qty=8, do_not_submit=True)
		dn.append(
			"items",
			{
				"item_code": "_Test Item",
				"warehouse": "_Test Warehouse - _TC",
				"qty": 1,
				"rate": 100,
				"conversion_factor": 1.0,
				"expense_account": "Cost of Goods Sold - _TC",
				"cost_center": "_Test Cost Center - _TC",
			},
		)
		dn.submit()

		si1 = make_sales_invoice(dn.name)
		si1.items[0].qty = 4
		si1.items.pop(1)
		si1.save()
		si1.submit()

		dn1 = create_delivery_note(is_return=1, return_against=dn.name, qty=-2, do_not_submit=True)
		dn1.items[0].dn_detail = dn.items[0].name
		dn1.submit()

		si2 = make_sales_invoice(dn.name)
		self.assertEqual(si2.items[0].qty, 2)
		self.assertEqual(si2.items[1].qty, 1)

	def test_delivery_note_bundle_with_batched_item(self):
		frappe.db.set_single_value("Stock Settings", "use_serial_batch_fields", 0)

		batched_bundle = make_item("_Test Batched bundle", {"is_stock_item": 0})
		batched_item = make_item(
			"_Test Batched Item",
			{
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "TESTBATCHIUU.#####",
			},
		)
		make_product_bundle(parent=batched_bundle.name, items=[batched_item.name])
		make_stock_entry(item_code=batched_item.name, target="_Test Warehouse - _TC", qty=10, basic_rate=42)

		dn = create_delivery_note(item_code=batched_bundle.name, qty=1)
		dn.load_from_db()

		batch_no = get_batch_from_bundle(dn.packed_items[0].serial_and_batch_bundle)
		packed_name = dn.packed_items[0].name
		self.assertTrue(batch_no)

		dn.cancel()

		# Cancel the reposting entry
		reposting_entries = frappe.get_all("Repost Item Valuation", filters={"docstatus": 1})
		for entry in reposting_entries:
			doc = frappe.get_doc("Repost Item Valuation", entry.name)
			doc.cancel()
			doc.delete()

		frappe.db.set_single_value("Accounts Settings", "delete_linked_ledger_entries", 1)

		dn.reload()
		dn.delete()

		bundle = frappe.db.get_value("Serial and Batch Bundle", {"voucher_detail_no": packed_name}, "name")
		self.assertFalse(bundle)

		frappe.db.set_single_value("Stock Settings", "use_serial_batch_fields", 1)
		frappe.db.set_single_value("Accounts Settings", "delete_linked_ledger_entries", 0)

	def test_payment_terms_are_fetched_when_creating_sales_invoice(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			create_payment_terms_template,
		)
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice

		automatically_fetch_payment_terms()

		so = make_sales_order(uom="Nos", do_not_save=1)
		create_payment_terms_template()
		so.payment_terms_template = "Test Receivable Template"
		so.submit()

		dn = create_dn_against_so(so.name, delivered_qty=10)

		si = create_sales_invoice(qty=10, do_not_save=1)
		si.items[0].delivery_note = dn.name
		si.items[0].dn_detail = dn.items[0].name
		si.items[0].sales_order = so.name
		si.items[0].so_detail = so.items[0].name

		si.insert()
		si.submit()

		self.assertEqual(so.payment_terms_template, si.payment_terms_template)
		compare_payment_schedules(self, so, si)

		automatically_fetch_payment_terms(enable=0)

	def test_returned_qty_in_return_dn(self):
		# SO ---> SI ---> DN
		#                 |
		#                 |---> DN(Partial Sales Return) ---> SI(Credit Note)
		#                 |
		#                 |---> DN(Partial Sales Return) ---> SI(Credit Note)

		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_delivery_note
		from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice

		so = make_sales_order(qty=10)
		si = make_sales_invoice(so.name)
		si.insert()
		si.submit()
		dn = make_delivery_note(si.name)
		dn.insert()
		dn.submit()
		self.assertEqual(dn.items[0].returned_qty, 0)
		self.assertEqual(dn.per_billed, 100)

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		dn1 = create_delivery_note(is_return=1, return_against=dn.name, qty=-3)
		si1 = make_sales_invoice(dn1.name)
		si1.update_billed_amount_in_delivery_note = True
		si1.insert()
		si1.submit()
		dn1.reload()
		self.assertEqual(dn1.items[0].returned_qty, 0)
		self.assertEqual(dn1.per_billed, 100)

		dn2 = create_delivery_note(is_return=1, return_against=dn.name, qty=-4)
		si2 = make_sales_invoice(dn2.name)
		si2.update_billed_amount_in_delivery_note = True
		si2.insert()
		si2.submit()
		dn2.reload()
		self.assertEqual(dn2.items[0].returned_qty, 0)
		self.assertEqual(dn2.per_billed, 100)

	def test_internal_transfer_with_valuation_only(self):
		from erpnext.selling.doctype.customer.test_customer import create_internal_customer

		item = make_item().name
		warehouse = "_Test Warehouse - _TC"
		target = "Stores - _TC"
		company = "_Test Company"
		customer = create_internal_customer(represents_company=company)
		rate = 42

		# Create item price and pricing rule
		frappe.get_doc(
			{
				"item_code": item,
				"price_list": "Standard Selling",
				"price_list_rate": 1000,
				"doctype": "Item Price",
			}
		).insert()

		frappe.get_doc(
			{
				"doctype": "Pricing Rule",
				"title": frappe.generate_hash(),
				"apply_on": "Item Code",
				"price_or_product_discount": "Price",
				"selling": 1,
				"company": company,
				"margin_type": "Percentage",
				"margin_rate_or_amount": 10,
				"apply_discount_on": "Grand Total",
				"items": [
					{
						"item_code": item,
					}
				],
			}
		).insert()

		make_stock_entry(target=warehouse, qty=5, basic_rate=rate, item_code=item)
		dn = create_delivery_note(
			item_code=item,
			company=company,
			customer=customer,
			qty=5,
			rate=500,
			warehouse=warehouse,
			target_warehouse=target,
			ignore_pricing_rule=0,
			do_not_save=True,
			do_not_submit=True,
		)

		dn.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": "_Test Account Service Tax - _TC",
				"description": "Tax 1",
				"rate": 14,
				"cost_center": "_Test Cost Center - _TC",
				"included_in_print_rate": 1,
			},
		)

		self.assertEqual(dn.items[0].rate, 500)  # haven't saved yet
		dn.save()
		self.assertEqual(dn.ignore_pricing_rule, 1)
		self.assertEqual(dn.taxes[0].included_in_print_rate, 0)

		# rate should reset to incoming rate
		self.assertEqual(dn.items[0].rate, rate)

		# rate should reset again if discounts are fiddled with
		dn.items[0].margin_type = "Amount"
		dn.items[0].margin_rate_or_amount = 50
		dn.save()

		self.assertEqual(dn.items[0].rate, rate)
		self.assertEqual(dn.items[0].net_rate, rate)

	def test_internal_transfer_precision_gle(self):
		from erpnext.selling.doctype.customer.test_customer import create_internal_customer

		item = make_item(properties={"valuation_method": "Moving Average"}).name
		company = "_Test Company with perpetual inventory"
		warehouse = "Stores - TCP1"
		target = "Finished Goods - TCP1"
		customer = create_internal_customer(represents_company=company)

		# average rate = 128.015
		rates = [101.45, 150.46, 138.25, 121.9]

		for rate in rates:
			make_stock_entry(item_code=item, target=warehouse, qty=1, rate=rate)

		dn = create_delivery_note(
			item_code=item,
			company=company,
			customer=customer,
			qty=4,
			warehouse=warehouse,
			target_warehouse=target,
		)
		self.assertFalse(frappe.db.exists("GL Entry", {"voucher_no": dn.name, "voucher_type": dn.doctype}))

	def test_batch_expiry_for_delivery_note(self):
		from erpnext.controllers.sales_and_purchase_return import make_return_doc
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		item = make_item(
			"_Test Batch Item For Return Check",
			{
				"is_purchase_item": 1,
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "TBIRC.#####",
			},
		)

		pi = make_purchase_receipt(qty=1, item_code=item.name)

		pr_batch_no = get_batch_from_bundle(pi.items[0].serial_and_batch_bundle)
		dn = create_delivery_note(qty=1, item_code=item.name, batch_no=pr_batch_no)

		dn.load_from_db()
		batch_no = get_batch_from_bundle(dn.items[0].serial_and_batch_bundle)
		self.assertTrue(batch_no)

		frappe.db.set_value("Batch", batch_no, "expiry_date", add_days(today(), -1))

		return_dn = make_return_doc(dn.doctype, dn.name)
		return_dn.save().submit()

		self.assertTrue(return_dn.docstatus == 1)

	def test_reserve_qty_on_sales_return(self):
		frappe.db.set_single_value("Selling Settings", "dont_reserve_sales_order_qty_on_sales_return", 0)
		self.reserved_qty_check()

	def test_dont_reserve_qty_on_sales_return(self):
		frappe.db.set_single_value("Selling Settings", "dont_reserve_sales_order_qty_on_sales_return", 1)
		self.reserved_qty_check()

	def reserved_qty_check(self):
		from erpnext.controllers.sales_and_purchase_return import make_return_doc
		from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
		from erpnext.stock.stock_balance import get_reserved_qty

		dont_reserve_qty = frappe.db.get_single_value(
			"Selling Settings", "dont_reserve_sales_order_qty_on_sales_return"
		)

		item = make_item().name
		warehouse = "_Test Warehouse - _TC"
		qty_to_reserve = 5

		so = make_sales_order(item_code=item, qty=qty_to_reserve)

		# Make qty avl for test.
		make_stock_entry(item_code=item, to_warehouse=warehouse, qty=10, basic_rate=100)

		# Test that item qty has been reserved on submit of sales order.
		self.assertEqual(get_reserved_qty(item, warehouse), qty_to_reserve)

		dn = make_delivery_note(so.name)
		dn.save().submit()

		# Test that item qty is no longer reserved since qty has been delivered.
		self.assertEqual(get_reserved_qty(item, warehouse), 0)

		dn_return = make_return_doc("Delivery Note", dn.name)
		dn_return.save().submit()

		returned = frappe.get_doc("Delivery Note", dn_return.name)
		returned.update_prevdoc_status()

		# Test that item qty is not reserved on sales return, if selling setting don't reserve qty is checked.
		self.assertEqual(get_reserved_qty(item, warehouse), 0 if dont_reserve_qty else qty_to_reserve)

	def tearDown(self):
		frappe.db.rollback()
		frappe.db.set_single_value("Selling Settings", "dont_reserve_sales_order_qty_on_sales_return", 0)

	def test_non_internal_transfer_delivery_note(self):
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		dn = create_delivery_note(do_not_submit=True)
		warehouse = create_warehouse("Internal Transfer Warehouse", company=dn.company)
		dn.items[0].db_set("target_warehouse", warehouse)

		dn.reload()

		self.assertEqual(dn.items[0].target_warehouse, warehouse)

		dn.save()
		dn.reload()
		self.assertFalse(dn.items[0].target_warehouse)

	def test_serial_no_status(self):
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		item = make_item(
			"Test Serial Item For Status",
			{"has_serial_no": 1, "is_stock_item": 1, "serial_no_series": "TESTSERIAL.#####"},
		)

		item_code = item.name
		pi = make_purchase_receipt(qty=1, item_code=item.name)
		pi.reload()
		serial_no = get_serial_nos_from_bundle(pi.items[0].serial_and_batch_bundle)

		self.assertEqual(frappe.db.get_value("Serial No", serial_no, "status"), "Active")

		dn = create_delivery_note(qty=1, item_code=item_code, serial_no=serial_no)
		dn.reload()
		self.assertEqual(frappe.db.get_value("Serial No", serial_no, "status"), "Delivered")

	def test_sales_return_valuation_for_moving_average(self):
		item_code = make_item(
			"_Test Item Sales Return with MA", {"is_stock_item": 1, "valuation_method": "Moving Average"}
		).name

		make_stock_entry(
			item_code=item_code,
			target="_Test Warehouse - _TC",
			qty=5,
			basic_rate=100.0,
			posting_date=add_days(nowdate(), -5),
		)
		dn = create_delivery_note(item_code=item_code, qty=5, rate=500, posting_date=add_days(nowdate(), -4))
		self.assertEqual(dn.items[0].incoming_rate, 100.0)

		make_stock_entry(
			item_code=item_code,
			target="_Test Warehouse - _TC",
			qty=5,
			basic_rate=200.0,
			posting_date=add_days(nowdate(), -3),
		)
		make_stock_entry(
			item_code=item_code,
			target="_Test Warehouse - _TC",
			qty=5,
			basic_rate=300.0,
			posting_date=add_days(nowdate(), -2),
		)

		dn1 = create_delivery_note(
			is_return=1,
			item_code=item_code,
			return_against=dn.name,
			qty=-5,
			rate=500,
			company=dn.company,
			expense_account="Cost of Goods Sold - _TC",
			cost_center="Main - _TC",
			do_not_submit=1,
			posting_date=add_days(nowdate(), -1),
		)

		# (300 * 5) + (200 * 5) = 2500
		# 2500 / 10 = 250

		self.assertAlmostEqual(dn1.items[0].incoming_rate, 250.0)

	def test_sales_return_valuation_for_moving_average_case2(self):
		# Make DN return
		# Make Bakcdated Purchase Receipt and check DN return valuation rate
		# The rate should be recalculate based on the backdated purchase receipt
		frappe.flags.print_debug_messages = False
		item_code = make_item(
			"_Test Item Sales Return with MA Case2",
			{"is_stock_item": 1, "valuation_method": "Moving Average", "stock_uom": "Nos"},
		).name

		make_stock_entry(
			item_code=item_code,
			target="_Test Warehouse - _TC",
			qty=5,
			basic_rate=100.0,
			posting_date=add_days(nowdate(), -5),
		)

		dn = create_delivery_note(
			item_code=item_code,
			warehouse="_Test Warehouse - _TC",
			qty=5,
			rate=500,
			posting_date=add_days(nowdate(), -4),
		)

		returned_dn = create_delivery_note(
			is_return=1,
			item_code=item_code,
			return_against=dn.name,
			qty=-5,
			rate=500,
			company=dn.company,
			warehouse="_Test Warehouse - _TC",
			expense_account="Cost of Goods Sold - _TC",
			cost_center="Main - _TC",
			posting_date=add_days(nowdate(), -1),
		)

		self.assertAlmostEqual(returned_dn.items[0].incoming_rate, 100.0)

		# Make backdated purchase receipt
		make_stock_entry(
			item_code=item_code,
			target="_Test Warehouse - _TC",
			qty=5,
			basic_rate=200.0,
			posting_date=add_days(nowdate(), -3),
		)

		returned_dn.reload()
		self.assertAlmostEqual(returned_dn.items[0].incoming_rate, 200.0)

	def test_batch_with_non_stock_uom(self):
		frappe.db.set_single_value("Stock Settings", "auto_create_serial_and_batch_bundle_for_outward", 1)

		item = make_item(
			properties={
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "TESTBATCH.#####",
				"stock_uom": "Nos",
			}
		)
		if not frappe.db.exists("UOM Conversion Detail", {"parent": item.name, "uom": "Kg"}):
			item.append("uoms", {"uom": "Kg", "conversion_factor": 5.0})
			item.save()

		item_code = item.name

		make_stock_entry(item_code=item_code, target="_Test Warehouse - _TC", qty=5, basic_rate=100.0)
		dn = create_delivery_note(
			item_code=item_code, qty=1, rate=500, warehouse="_Test Warehouse - _TC", do_not_save=True
		)
		dn.items[0].uom = "Kg"
		dn.items[0].conversion_factor = 5.0

		dn.save()
		dn.submit()

		self.assertEqual(dn.items[0].stock_qty, 5.0)
		voucher_detail_no = dn.items[0].name
		delivered_batch_qty = frappe.db.get_value(
			"Serial and Batch Bundle", {"voucher_detail_no": voucher_detail_no}, "total_qty"
		)
		self.assertEqual(abs(delivered_batch_qty), 5.0)

		frappe.db.set_single_value("Stock Settings", "auto_create_serial_and_batch_bundle_for_outward", 0)

	def test_internal_transfer_for_non_stock_item(self):
		from erpnext.selling.doctype.customer.test_customer import create_internal_customer
		from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note

		item = make_item(properties={"is_stock_item": 0}).name
		warehouse = "_Test Warehouse - _TC"
		target = "Stores - _TC"
		company = "_Test Company"
		customer = create_internal_customer(represents_company=company)
		rate = 100

		so = make_sales_order(item_code=item, qty=1, rate=rate, customer=customer, warehouse=warehouse)
		dn = make_delivery_note(so.name)
		dn.items[0].target_warehouse = target
		dn.save().submit()

		self.assertEqual(so.items[0].rate, rate)
		self.assertEqual(dn.items[0].rate, so.items[0].rate)

	def test_use_serial_batch_fields_for_packed_items(self):
		bundle_item = make_item("Test _Packed Product Bundle Item ", {"is_stock_item": 0})
		serial_item = make_item(
			"Test _Packed Serial Item ",
			{"is_stock_item": 1, "has_serial_no": 1, "serial_no_series": "SN-TESTSERIAL-.#####"},
		)
		batch_item = make_item(
			"Test _Packed Batch Item ",
			{
				"is_stock_item": 1,
				"has_batch_no": 1,
				"batch_number_series": "BATCH-TESTSERIAL-.#####",
				"create_new_batch": 1,
			},
		)
		make_product_bundle(parent=bundle_item.name, items=[serial_item.name, batch_item.name])

		item_details = {}
		for item in [serial_item, batch_item]:
			se = make_stock_entry(item_code=item.name, target="_Test Warehouse - _TC", qty=5, basic_rate=100)
			item_details[item.name] = se.items[0].serial_and_batch_bundle

		dn = create_delivery_note(item_code=bundle_item.name, qty=1, do_not_submit=True)
		serial_no = ""
		for row in dn.packed_items:
			row.use_serial_batch_fields = 1

			if row.item_code == serial_item.name:
				serial_and_batch_bundle = item_details[serial_item.name]
				row.serial_no = get_serial_nos_from_bundle(serial_and_batch_bundle)[3]
				serial_no = row.serial_no
			else:
				serial_and_batch_bundle = item_details[batch_item.name]
				row.batch_no = get_batch_from_bundle(serial_and_batch_bundle)

		dn.submit()
		dn.load_from_db()

		for row in dn.packed_items:
			self.assertTrue(row.serial_no or row.batch_no)
			self.assertTrue(row.serial_and_batch_bundle)

			if row.serial_no:
				self.assertEqual(row.serial_no, serial_no)

	def test_delivery_note_legacy_serial_no_valuation(self):
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_return
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		frappe.flags.ignore_serial_batch_bundle_validation = True
		sn_item = "Old Serial NO Item Valuation Test - 2"
		make_item(
			sn_item,
			{
				"has_serial_no": 1,
				"serial_no_series": "SN-SOVOSN-.####",
				"is_stock_item": 1,
			},
		)

		serial_nos = [
			"SN-SOVOSN-1234",
			"SN-SOVOSN-2234",
		]

		for sn in serial_nos:
			if not frappe.db.exists("Serial No", sn):
				sn_doc = frappe.get_doc(
					{
						"doctype": "Serial No",
						"item_code": sn_item,
						"serial_no": sn,
					}
				)
				sn_doc.insert()

		warehouse = "_Test Warehouse - _TC"
		company = frappe.db.get_value("Warehouse", warehouse, "company")
		se_doc = make_stock_entry(
			item_code=sn_item,
			company=company,
			target="_Test Warehouse - _TC",
			qty=2,
			basic_rate=150,
			do_not_submit=1,
			use_serial_batch_fields=0,
		)
		se_doc.submit()

		se_doc.items[0].db_set("serial_no", "\n".join(serial_nos))

		sle_data = frappe.get_all(
			"Stock Ledger Entry",
			filters={"voucher_no": se_doc.name, "voucher_type": "Stock Entry"},
		)[0]

		sle_doc = frappe.get_doc("Stock Ledger Entry", sle_data.name)
		self.assertFalse(sle_doc.serial_no)
		sle_doc.db_set("serial_no", "\n".join(serial_nos))
		sle_doc.reload()
		self.assertTrue(sle_doc.serial_no)
		self.assertFalse(sle_doc.is_cancelled)

		for sn in serial_nos:
			sn_doc = frappe.get_doc("Serial No", sn)
			sn_doc.db_set(
				{
					"status": "Active",
					"warehouse": warehouse,
				}
			)

		self.assertEqual(sorted(get_serial_nos(se_doc.items[0].serial_no)), sorted(serial_nos))
		frappe.flags.ignore_serial_batch_bundle_validation = False

		se_doc = make_stock_entry(
			item_code=sn_item,
			company=company,
			target="_Test Warehouse - _TC",
			qty=2,
			basic_rate=200,
		)

		serial_nos.extend(get_serial_nos_from_bundle(se_doc.items[0].serial_and_batch_bundle))

		dn = create_delivery_note(
			item_code=sn_item,
			qty=3,
			rate=500,
			warehouse=warehouse,
			company=company,
			expense_account="Cost of Goods Sold - _TC",
			cost_center="Main - _TC",
			use_serial_batch_fields=1,
			serial_no="\n".join(serial_nos[0:3]),
		)

		dn.reload()

		sle_data = frappe.get_all(
			"Stock Ledger Entry",
			filters={"voucher_no": dn.name, "voucher_type": "Delivery Note"},
			fields=["stock_value_difference", "actual_qty"],
		)[0]

		self.assertEqual(sle_data.actual_qty, 3 * -1)
		self.assertEqual(sle_data.stock_value_difference, 500.0 * -1)

		dn = create_delivery_note(
			item_code=sn_item,
			qty=1,
			rate=500,
			warehouse=warehouse,
			company=company,
			expense_account="Cost of Goods Sold - _TC",
			cost_center="Main - _TC",
			use_serial_batch_fields=1,
			serial_no=serial_nos[-1],
		)

		dn.reload()

		sle_data = frappe.get_all(
			"Stock Ledger Entry",
			filters={"voucher_no": dn.name, "voucher_type": "Delivery Note"},
			fields=["stock_value_difference", "actual_qty"],
		)[0]

		self.assertEqual(sle_data.actual_qty, 1 * -1)
		self.assertEqual(sle_data.stock_value_difference, 200.0 * -1)

	def test_sales_return_batch_no_for_batched_item_in_dn(self):
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_return

		item_code = make_item(
			"Test Batched Item for Sales Return 11",
			properties={
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "B11-TESTBATCH.#####",
				"is_stock_item": 1,
			},
		).name

		se = make_stock_entry(item_code=item_code, target="_Test Warehouse - _TC", qty=5, basic_rate=100)

		batch_no = get_batch_from_bundle(se.items[0].serial_and_batch_bundle)
		dn = create_delivery_note(
			item_code=item_code,
			qty=5,
			rate=500,
			use_serial_batch_fields=0,
			batch_no=batch_no,
		)

		dn_return = make_sales_return(dn.name)
		dn_return.save().submit()
		returned_batch_no = get_batch_from_bundle(dn_return.items[0].serial_and_batch_bundle)
		self.assertEqual(batch_no, returned_batch_no)

	def test_partial_sales_return_batch_no_for_batched_item_in_dn(self):
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_return

		item_code = make_item(
			"Test Partial Batched Item for Sales Return 11",
			properties={
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "BPART11-TESTBATCH.#####",
				"is_stock_item": 1,
			},
		).name

		se = make_stock_entry(item_code=item_code, target="_Test Warehouse - _TC", qty=5, basic_rate=100)

		batch_no = get_batch_from_bundle(se.items[0].serial_and_batch_bundle)
		dn = create_delivery_note(
			item_code=item_code,
			qty=5,
			rate=500,
			use_serial_batch_fields=0,
			batch_no=batch_no,
		)

		dn_return = make_sales_return(dn.name)
		dn_return.items[0].qty = 3 * -1
		dn_return.save().submit()

		returned_batch_no = get_batch_from_bundle(dn_return.items[0].serial_and_batch_bundle)
		self.assertEqual(batch_no, returned_batch_no)
		sabb_qty = frappe.db.get_value(
			"Serial and Batch Bundle", dn_return.items[0].serial_and_batch_bundle, "total_qty"
		)
		self.assertEqual(sabb_qty, 3)

		dn_return = make_sales_return(dn.name)
		dn_return.items[0].qty = 2 * -1
		dn_return.save().submit()

		returned_batch_no = get_batch_from_bundle(dn_return.items[0].serial_and_batch_bundle)
		self.assertEqual(batch_no, returned_batch_no)

		sabb_qty = frappe.db.get_value(
			"Serial and Batch Bundle", dn_return.items[0].serial_and_batch_bundle, "total_qty"
		)
		self.assertEqual(sabb_qty, 2)

	def test_sales_return_serial_no_for_serial_item_in_dn(self):
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_return

		item_code = make_item(
			"Test Serial Item for Sales Return 11",
			properties={
				"has_serial_no": 1,
				"serial_no_series": "SNN11-TESTBATCH.#####",
				"is_stock_item": 1,
			},
		).name

		se = make_stock_entry(item_code=item_code, target="_Test Warehouse - _TC", qty=5, basic_rate=100)

		serial_nos = get_serial_nos_from_bundle(se.items[0].serial_and_batch_bundle)
		dn = create_delivery_note(
			item_code=item_code,
			qty=5,
			rate=500,
			use_serial_batch_fields=0,
			serial_no=serial_nos,
		)

		dn_return = make_sales_return(dn.name)
		dn_return.save().submit()
		returned_serial_nos = get_serial_nos_from_bundle(dn_return.items[0].serial_and_batch_bundle)
		self.assertEqual(serial_nos, returned_serial_nos)


def create_delivery_note(**args):
	dn = frappe.new_doc("Delivery Note")
	args = frappe._dict(args)
	dn.posting_date = args.posting_date or nowdate()
	dn.posting_time = args.posting_time or nowtime()
	dn.set_posting_time = 1

	dn.company = args.company or "_Test Company"
	dn.customer = args.customer or "_Test Customer"
	dn.currency = args.currency or "INR"
	dn.is_return = args.is_return
	dn.return_against = args.return_against

	bundle_id = None
	if not args.use_serial_batch_fields and (args.get("batch_no") or args.get("serial_no")):
		type_of_transaction = args.type_of_transaction or "Outward"

		if dn.is_return:
			type_of_transaction = "Inward"

		qty = args.get("qty") or 1
		qty *= -1 if type_of_transaction == "Outward" else 1
		batches = {}
		if args.get("batch_no"):
			batches = frappe._dict({args.batch_no: qty})

		bundle_id = make_serial_batch_bundle(
			frappe._dict(
				{
					"item_code": args.item or args.item_code or "_Test Item",
					"warehouse": args.warehouse or "_Test Warehouse - _TC",
					"qty": qty,
					"batches": batches,
					"voucher_type": "Delivery Note",
					"serial_nos": args.serial_no,
					"posting_date": dn.posting_date,
					"posting_time": dn.posting_time,
					"type_of_transaction": type_of_transaction,
					"do_not_submit": True,
				}
			)
		).name

	dn.append(
		"items",
		{
			"item_code": args.item or args.item_code or "_Test Item",
			"warehouse": args.warehouse or "_Test Warehouse - _TC",
			"qty": args.qty or 1,
			"rate": args.rate if args.get("rate") is not None else 100,
			"conversion_factor": 1.0,
			"serial_and_batch_bundle": bundle_id,
			"allow_zero_valuation_rate": args.allow_zero_valuation_rate or 1,
			"expense_account": args.expense_account or "Cost of Goods Sold - _TC",
			"cost_center": args.cost_center or "_Test Cost Center - _TC",
			"target_warehouse": args.target_warehouse,
			"use_serial_batch_fields": args.use_serial_batch_fields,
			"serial_no": args.serial_no if args.use_serial_batch_fields else None,
			"batch_no": args.batch_no if args.use_serial_batch_fields else None,
		},
	)

	if not args.do_not_save:
		dn.insert()
		if not args.do_not_submit:
			dn.submit()

		dn.load_from_db()

	return dn


test_dependencies = ["Product Bundle"]
