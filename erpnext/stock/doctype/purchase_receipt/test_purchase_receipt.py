# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from datetime import date, datetime

import frappe
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import add_days, cint, cstr, flt, get_datetime, getdate, nowtime, today
from pypika import functions as fn

import erpnext
from erpnext.accounts.doctype.account.test_account import create_account, get_inventory_account
from erpnext.buying.doctype.supplier.test_supplier import create_supplier
from erpnext.controllers.accounts_controller import InvalidQtyError
from erpnext.controllers.buying_controller import QtyMismatchError
from erpnext.controllers.stock_controller import get_stock_ledger_preview
from erpnext.stock import get_warehouse_account_map
from erpnext.stock.doctype.item.test_item import create_item, make_item
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice
from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
	SerialNoDuplicateError,
	SerialNoExistsInFutureTransactionError,
)
from erpnext.stock.doctype.serial_and_batch_bundle.test_serial_and_batch_bundle import (
	get_batch_from_bundle,
	get_serial_nos_from_bundle,
	make_serial_batch_bundle,
)
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
from erpnext.stock.utils import get_incoming_rate, get_stock_balance


class TestPurchaseReceipt(FrappeTestCase):
	def setUp(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
		from erpnext.regional.doctype.import_supplier_invoice.import_supplier_invoice import create_uom

		create_company()
		create_warehouse(
			warehouse_name="_Test Warehouse 1 - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC"},
			company="_Test Company",
		)
		create_uom("_Test UOM")
		frappe.db.set_single_value("Buying Settings", "allow_multiple_items", 1)

	def test_purchase_receipt_qty(self):
		pr = make_purchase_receipt(qty=0, rejected_qty=0, do_not_save=True)
		with self.assertRaises(InvalidQtyError):
			pr.save()

		# No error with qty=1
		pr.items[0].qty = 1
		pr.save()
		self.assertEqual(pr.items[0].qty, 1)

		# No error with rejected_qty=1
		pr.items[0].rejected_warehouse = "_Test Rejected Warehouse - _TC"
		pr.items[0].rejected_qty = 1
		pr.items[0].qty = 0
		pr.save()
		self.assertEqual(pr.items[0].rejected_qty, 1)

	def test_purchase_receipt_received_qty(self):
		"""
		1. Test if received qty is validated against accepted + rejected
		2. Test if received qty is auto set on save
		"""
		pr = make_purchase_receipt(
			qty=1, rejected_qty=1, received_qty=3, item_code="_Test Item Home Desktop 200", do_not_save=True
		)
		self.assertRaises(QtyMismatchError, pr.save)

		pr.items[0].received_qty = 0
		pr.save()
		self.assertEqual(pr.items[0].received_qty, 2)

		# teardown
		pr.delete()

	def test_reverse_purchase_receipt_sle(self):
		pr = make_purchase_receipt(qty=0.5, item_code="_Test Item Home Desktop 200")

		sl_entry = frappe.db.get_all(
			"Stock Ledger Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": pr.name},
			["actual_qty"],
		)

		self.assertEqual(len(sl_entry), 1)
		self.assertEqual(sl_entry[0].actual_qty, 0.5)

		pr.cancel()

		sl_entry_cancelled = frappe.db.get_all(
			"Stock Ledger Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": pr.name},
			["actual_qty"],
			order_by="creation",
		)

		self.assertEqual(len(sl_entry_cancelled), 2)
		self.assertEqual(sl_entry_cancelled[1].actual_qty, -0.5)

	def test_make_purchase_invoice(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_term

		create_payment_term("_Test Payment Term 1 for Purchase Invoice")
		create_payment_term("_Test Payment Term 2 for Purchase Invoice")

		if not frappe.db.exists(
			"Payment Terms Template", "_Test Payment Terms Template For Purchase Invoice"
		):
			frappe.get_doc(
				{
					"doctype": "Payment Terms Template",
					"template_name": "_Test Payment Terms Template For Purchase Invoice",
					"allocate_payment_based_on_payment_terms": 1,
					"terms": [
						{
							"doctype": "Payment Terms Template Detail",
							"payment_term": "_Test Payment Term 1 for Purchase Invoice",
							"invoice_portion": 50.00,
							"credit_days_based_on": "Day(s) after invoice date",
							"credit_days": 00,
						},
						{
							"doctype": "Payment Terms Template Detail",
							"payment_term": "_Test Payment Term 2 for Purchase Invoice",
							"invoice_portion": 50.00,
							"credit_days_based_on": "Day(s) after invoice date",
							"credit_days": 30,
						},
					],
				}
			).insert()

		template = frappe.db.get_value(
			"Payment Terms Template", "_Test Payment Terms Template For Purchase Invoice"
		)
		old_template_in_supplier = frappe.db.get_value("Supplier", "_Test Supplier", "payment_terms")
		frappe.db.set_value("Supplier", "_Test Supplier", "payment_terms", template)

		pr = make_purchase_receipt(do_not_save=True)
		self.assertRaises(frappe.ValidationError, make_purchase_invoice, pr.name)
		pr.submit()

		pi = make_purchase_invoice(pr.name)

		self.assertEqual(pi.doctype, "Purchase Invoice")
		self.assertEqual(len(pi.get("items")), len(pr.get("items")))

		# test maintaining same rate throughout purchade cycle
		pi.get("items")[0].rate = 200
		self.assertRaises(frappe.ValidationError, frappe.get_doc(pi).submit)

		# test if payment terms are fetched and set in PI
		self.assertEqual(pi.payment_terms_template, template)
		self.assertEqual(pi.payment_schedule[0].payment_amount, flt(pi.grand_total) / 2)
		self.assertEqual(pi.payment_schedule[0].invoice_portion, 50)
		self.assertEqual(pi.payment_schedule[1].payment_amount, flt(pi.grand_total) / 2)
		self.assertEqual(pi.payment_schedule[1].invoice_portion, 50)

		# teardown
		pi.delete()  # draft PI
		pr.cancel()
		frappe.db.set_value("Supplier", "_Test Supplier", "payment_terms", old_template_in_supplier)
		frappe.get_doc("Payment Terms Template", "_Test Payment Terms Template For Purchase Invoice").delete()

	def test_purchase_receipt_no_gl_entry(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		existing_bin_qty, existing_bin_stock_value = frappe.db.get_value(
			"Bin",
			{"item_code": "_Test Item", "warehouse": "_Test Warehouse - _TC"},
			["actual_qty", "stock_value"],
		)

		if existing_bin_qty < 0:
			make_stock_entry(
				item_code="_Test Item", target="_Test Warehouse - _TC", qty=abs(existing_bin_qty)
			)

		existing_bin_qty, existing_bin_stock_value = frappe.db.get_value(
			"Bin",
			{"item_code": "_Test Item", "warehouse": "_Test Warehouse - _TC"},
			["actual_qty", "stock_value"],
		)

		pr = make_purchase_receipt()

		stock_value_difference = frappe.db.get_value(
			"Stock Ledger Entry",
			{
				"voucher_type": "Purchase Receipt",
				"voucher_no": pr.name,
				"item_code": "_Test Item",
				"warehouse": "_Test Warehouse - _TC",
			},
			"stock_value_difference",
		)

		self.assertEqual(stock_value_difference, 250)

		current_bin_stock_value = frappe.db.get_value(
			"Bin", {"item_code": "_Test Item", "warehouse": "_Test Warehouse - _TC"}, "stock_value"
		)
		self.assertEqual(current_bin_stock_value, existing_bin_stock_value + 250)

		self.assertFalse(get_gl_entries("Purchase Receipt", pr.name))

		pr.cancel()

	def test_batched_serial_no_purchase(self):
		item = frappe.db.exists("Item", {"item_name": "Batched Serialized Item"})
		if not item:
			item = create_item("Batched Serialized Item")
			item.has_batch_no = 1
			item.create_new_batch = 1
			item.has_serial_no = 1
			item.batch_number_series = "BS-BATCH-.##"
			item.serial_no_series = "BS-.####"
			item.save()
		else:
			item = frappe.get_doc("Item", {"item_name": "Batched Serialized Item"})

		pr = make_purchase_receipt(item_code=item.name, qty=5, rate=500)

		self.assertTrue(frappe.db.get_value("Batch", {"item": item.name, "reference_name": pr.name}))

		pr.load_from_db()
		pr.cancel()

	def test_duplicate_serial_nos(self):
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

		item = frappe.db.exists("Item", {"item_name": "Test Serialized Item 123"})
		if not item:
			item = create_item("Test Serialized Item 123")
			item.has_serial_no = 1
			item.serial_no_series = "TSI123-.####"
			item.save()
		else:
			item = frappe.get_doc("Item", {"item_name": "Test Serialized Item 123"})

		# First make purchase receipt
		pr = make_purchase_receipt(item_code=item.name, qty=2, rate=500)
		pr.load_from_db()

		bundle_id = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": pr.name, "item_code": item.name},
			"serial_and_batch_bundle",
		)

		serial_nos = get_serial_nos_from_bundle(bundle_id)

		self.assertEqual(get_serial_nos_from_bundle(pr.items[0].serial_and_batch_bundle), serial_nos)

		bundle_id = make_serial_batch_bundle(
			frappe._dict(
				{
					"item_code": item.item_code,
					"warehouse": "_Test Warehouse 2 - _TC1",
					"company": "_Test Company 1",
					"qty": 2,
					"voucher_type": "Purchase Receipt",
					"serial_nos": serial_nos,
					"posting_date": today(),
					"posting_time": nowtime(),
					"do_not_save": True,
				}
			)
		)

		self.assertRaises(SerialNoDuplicateError, bundle_id.make_serial_and_batch_bundle)

		# Then made delivery note to remove the serial nos from stock
		dn = create_delivery_note(item_code=item.name, qty=2, rate=1500, serial_no=serial_nos)
		dn.load_from_db()
		self.assertEqual(get_serial_nos_from_bundle(dn.items[0].serial_and_batch_bundle), serial_nos)

		posting_date = add_days(today(), -3)

		# Try to receive same serial nos again in the same company with backdated.
		bundle_id = make_serial_batch_bundle(
			frappe._dict(
				{
					"item_code": item.item_code,
					"warehouse": "_Test Warehouse - _TC",
					"company": "_Test Company",
					"qty": 2,
					"rate": 500,
					"voucher_type": "Purchase Receipt",
					"serial_nos": serial_nos,
					"posting_date": posting_date,
					"posting_time": nowtime(),
					"do_not_save": True,
				}
			)
		)

		self.assertRaises(SerialNoExistsInFutureTransactionError, bundle_id.make_serial_and_batch_bundle)

		# Try to receive same serial nos with different company with backdated.
		bundle_id = make_serial_batch_bundle(
			frappe._dict(
				{
					"item_code": item.item_code,
					"warehouse": "_Test Warehouse 2 - _TC1",
					"company": "_Test Company 1",
					"qty": 2,
					"rate": 500,
					"voucher_type": "Purchase Receipt",
					"serial_nos": serial_nos,
					"posting_date": posting_date,
					"posting_time": nowtime(),
					"do_not_save": True,
				}
			)
		)

		self.assertRaises(SerialNoExistsInFutureTransactionError, bundle_id.make_serial_and_batch_bundle)

		# Receive the same serial nos after the delivery note posting date and time
		make_purchase_receipt(item_code=item.name, qty=2, rate=500, serial_no=serial_nos)

		# Raise the error for backdated deliver note entry cancel
		# self.assertRaises(SerialNoExistsInFutureTransactionError, dn.cancel)

	def test_purchase_receipt_gl_entry(self):
		pr = make_purchase_receipt(
			company="_Test Company with perpetual inventory",
			warehouse="Stores - TCP1",
			supplier_warehouse="Work In Progress - TCP1",
			get_multiple_items=True,
			get_taxes_and_charges=True,
		)

		self.assertEqual(cint(erpnext.is_perpetual_inventory_enabled(pr.company)), 1)

		gl_entries = get_gl_entries("Purchase Receipt", pr.name)

		self.assertTrue(gl_entries)

		stock_in_hand_account = get_inventory_account(pr.company, pr.items[0].warehouse)
		fixed_asset_account = get_inventory_account(pr.company, pr.items[1].warehouse)

		if stock_in_hand_account == fixed_asset_account:
			expected_values = {
				stock_in_hand_account: [750.0, 0.0],
				"Stock Received But Not Billed - TCP1": [0.0, 500.0],
				"_Test Account Shipping Charges - TCP1": [0.0, 100.0],
				"_Test Account Customs Duty - TCP1": [0.0, 150.0],
			}
		else:
			expected_values = {
				stock_in_hand_account: [375.0, 0.0],
				fixed_asset_account: [375.0, 0.0],
				"Stock Received But Not Billed - TCP1": [0.0, 500.0],
				"_Test Account Shipping Charges - TCP1": [0.0, 250.0],
			}
		for gle in gl_entries:
			self.assertEqual(expected_values[gle.account][0], gle.debit)
			self.assertEqual(expected_values[gle.account][1], gle.credit)

		pr.cancel()
		self.assertTrue(get_gl_entries("Purchase Receipt", pr.name))

	def test_serial_no_warehouse(self):
		pr = make_purchase_receipt(item_code="_Test Serialized Item With Series", qty=1)
		pr_row_1_serial_no = get_serial_nos_from_bundle(pr.get("items")[0].serial_and_batch_bundle)[0]

		self.assertEqual(
			frappe.db.get_value("Serial No", pr_row_1_serial_no, "warehouse"), pr.get("items")[0].warehouse
		)

		pr.cancel()
		self.assertFalse(frappe.db.get_value("Serial No", pr_row_1_serial_no, "warehouse"))

	def test_rejected_warehouse_filter(self):
		pr = frappe.copy_doc(test_records[0])
		pr.get("items")[0].item_code = "_Test Serialized Item With Series"
		pr.get("items")[0].qty = 3
		pr.get("items")[0].rejected_qty = 2
		pr.get("items")[0].received_qty = 5
		pr.get("items")[0].rejected_warehouse = pr.get("items")[0].warehouse
		self.assertRaises(frappe.ValidationError, pr.save)

	def test_rejected_serial_no(self):
		pr = frappe.copy_doc(test_records[0])
		pr.get("items")[0].item_code = "_Test Serialized Item With Series"
		pr.get("items")[0].qty = 3
		pr.get("items")[0].rejected_qty = 2
		pr.get("items")[0].received_qty = 5
		pr.get("items")[0].rejected_warehouse = "_Test Rejected Warehouse - _TC"
		pr.insert()
		pr.submit()
		pr.load_from_db()

		accepted_serial_nos = get_serial_nos_from_bundle(pr.get("items")[0].serial_and_batch_bundle)
		self.assertEqual(len(accepted_serial_nos), 3)
		for serial_no in accepted_serial_nos:
			self.assertEqual(
				frappe.db.get_value("Serial No", serial_no, "warehouse"), pr.get("items")[0].warehouse
			)

		rejected_serial_nos = get_serial_nos_from_bundle(pr.get("items")[0].rejected_serial_and_batch_bundle)
		self.assertEqual(len(rejected_serial_nos), 2)
		for serial_no in rejected_serial_nos:
			self.assertEqual(
				frappe.db.get_value("Serial No", serial_no, "warehouse"),
				pr.get("items")[0].rejected_warehouse,
			)

		pr.cancel()

	def test_purchase_return_partial(self):
		pr = make_purchase_receipt(
			company="_Test Company with perpetual inventory",
			warehouse="Stores - TCP1",
			supplier_warehouse="Work In Progress - TCP1",
		)

		return_pr = make_purchase_receipt(
			company="_Test Company with perpetual inventory",
			warehouse="Stores - TCP1",
			supplier_warehouse="Work In Progress - TCP1",
			is_return=1,
			return_against=pr.name,
			qty=-2,
			do_not_submit=1,
		)
		return_pr.items[0].purchase_receipt_item = pr.items[0].name
		return_pr.submit()

		# check sle
		outgoing_rate = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": return_pr.name},
			"outgoing_rate",
		)

		self.assertEqual(outgoing_rate, 50)

		# check gl entries for return
		gl_entries = get_gl_entries("Purchase Receipt", return_pr.name)

		self.assertTrue(gl_entries)
		stock_in_hand_account = get_inventory_account(return_pr.company)

		expected_values = {
			stock_in_hand_account: [0.0, 100.0],
			"Stock Received But Not Billed - TCP1": [100.0, 0.0],
		}

		for gle in gl_entries:
			self.assertEqual(expected_values[gle.account][0], gle.debit)
			self.assertEqual(expected_values[gle.account][1], gle.credit)

		# hack because new_doc isn't considering is_return portion of status_updater
		returned = frappe.get_doc("Purchase Receipt", return_pr.name)
		returned.update_prevdoc_status()
		pr.load_from_db()

		# Check if Original PR updated
		self.assertEqual(pr.items[0].returned_qty, 2)
		self.assertEqual(pr.per_returned, 40)

		from erpnext.controllers.sales_and_purchase_return import make_return_doc

		return_pr_2 = make_return_doc("Purchase Receipt", pr.name)

		# Check if unreturned amount is mapped in 2nd return
		self.assertEqual(return_pr_2.items[0].qty, -3)

		# Make PI against unreturned amount
		buying_settings = frappe.get_single("Buying Settings")
		buying_settings.bill_for_rejected_quantity_in_purchase_invoice = 0
		buying_settings.save()

		pi = make_purchase_invoice(pr.name)
		pi.submit()

		self.assertEqual(pi.items[0].qty, 3)

		buying_settings.bill_for_rejected_quantity_in_purchase_invoice = 1
		buying_settings.save()

		pr.load_from_db()
		# PR should be completed on billing all unreturned amount
		self.assertEqual(pr.items[0].billed_amt, 150)
		self.assertEqual(pr.per_billed, 100)
		self.assertEqual(pr.status, "Completed")

		pi.load_from_db()
		pi.cancel()

		pr.load_from_db()
		self.assertEqual(pr.per_billed, 0)

		return_pr.cancel()
		pr.cancel()

	def test_purchase_return_full(self):
		pr = make_purchase_receipt(
			company="_Test Company with perpetual inventory",
			warehouse="Stores - TCP1",
			supplier_warehouse="Work In Progress - TCP1",
		)

		return_pr = make_purchase_receipt(
			company="_Test Company with perpetual inventory",
			warehouse="Stores - TCP1",
			supplier_warehouse="Work In Progress - TCP1",
			is_return=1,
			return_against=pr.name,
			qty=-5,
			do_not_submit=1,
		)
		return_pr.items[0].purchase_receipt_item = pr.items[0].name
		return_pr.submit()

		# hack because new_doc isn't considering is_return portion of status_updater
		returned = frappe.get_doc("Purchase Receipt", return_pr.name)
		returned.update_prevdoc_status()
		pr.load_from_db()

		# Check if Original PR updated
		self.assertEqual(pr.items[0].returned_qty, 5)
		self.assertEqual(pr.per_returned, 100)
		self.assertEqual(pr.status, "Return Issued")

		return_pr.cancel()
		pr.cancel()

	def test_purchase_return_for_rejected_qty(self):
		from erpnext.stock.doctype.warehouse.test_warehouse import get_warehouse

		rejected_warehouse = "_Test Rejected Warehouse - TCP1"
		if not frappe.db.exists("Warehouse", rejected_warehouse):
			get_warehouse(
				company="_Test Company with perpetual inventory",
				abbr=" - TCP1",
				warehouse_name="_Test Rejected Warehouse",
			).name

		pr = make_purchase_receipt(
			company="_Test Company with perpetual inventory",
			warehouse="Stores - TCP1",
			supplier_warehouse="Work In Progress - TCP1",
			qty=2,
			rejected_qty=2,
			rejected_warehouse=rejected_warehouse,
		)

		return_pr = make_purchase_receipt(
			company="_Test Company with perpetual inventory",
			warehouse="Stores - TCP1",
			supplier_warehouse="Work In Progress - TCP1",
			is_return=1,
			return_against=pr.name,
			qty=-2,
			rejected_qty=-2,
			rejected_warehouse=rejected_warehouse,
		)

		actual_qty = frappe.db.get_value(
			"Stock Ledger Entry",
			{
				"voucher_type": "Purchase Receipt",
				"voucher_no": return_pr.name,
				"warehouse": return_pr.items[0].rejected_warehouse,
			},
			"actual_qty",
		)

		self.assertEqual(actual_qty, -2)

		return_pr.cancel()
		pr.cancel()

	def test_purchase_receipt_for_rejected_gle_without_accepted_warehouse(self):
		from erpnext.stock.doctype.warehouse.test_warehouse import get_warehouse

		rejected_warehouse = "_Test Rejected Warehouse - TCP1"
		if not frappe.db.exists("Warehouse", rejected_warehouse):
			get_warehouse(
				company="_Test Company with perpetual inventory",
				abbr=" - TCP1",
				warehouse_name="_Test Rejected Warehouse",
			).name

		pr = make_purchase_receipt(
			company="_Test Company with perpetual inventory",
			warehouse="Stores - TCP1",
			received_qty=2,
			rejected_qty=2,
			rejected_warehouse=rejected_warehouse,
			do_not_save=True,
		)

		pr.items[0].qty = 0.0
		pr.items[0].warehouse = ""
		pr.submit()

		actual_qty = frappe.db.get_value(
			"Stock Ledger Entry",
			{
				"voucher_type": "Purchase Receipt",
				"voucher_no": pr.name,
				"warehouse": pr.items[0].rejected_warehouse,
				"is_cancelled": 0,
			},
			"actual_qty",
		)

		self.assertEqual(actual_qty, 2)
		self.assertFalse(pr.items[0].warehouse)
		pr.cancel()

	def test_purchase_return_for_serialized_items(self):
		def _check_serial_no_values(serial_no, field_values):
			serial_no = frappe.get_doc("Serial No", serial_no)
			for field, value in field_values.items():
				self.assertEqual(cstr(serial_no.get(field)), value)

		pr = make_purchase_receipt(item_code="_Test Serialized Item With Series", qty=1)

		serial_no = get_serial_nos_from_bundle(pr.get("items")[0].serial_and_batch_bundle)[0]

		_check_serial_no_values(serial_no, {"warehouse": "_Test Warehouse - _TC"})

		return_pr = make_purchase_receipt(
			item_code="_Test Serialized Item With Series",
			qty=-1,
			is_return=1,
			return_against=pr.name,
			serial_no=[serial_no],
		)

		_check_serial_no_values(
			serial_no,
			{"warehouse": ""},
		)

		return_pr.cancel()
		pr.reload()
		pr.cancel()

	def test_purchase_return_for_multi_uom(self):
		item_code = "_Test Purchase Return For Multi-UOM"
		if not frappe.db.exists("Item", item_code):
			item = make_item(item_code, {"stock_uom": "Box"})
			row = item.append("uoms", {"uom": "Unit", "conversion_factor": 0.1})
			row.db_update()

		pr = make_purchase_receipt(item_code=item_code, qty=1, uom="Box", conversion_factor=1.0)
		return_pr = make_purchase_receipt(
			item_code=item_code,
			qty=-10,
			uom="Unit",
			stock_uom="Box",
			conversion_factor=0.1,
			is_return=1,
			return_against=pr.name,
		)

		self.assertEqual(abs(return_pr.items[0].stock_qty), 1.0)

		return_pr.cancel()
		pr.cancel()

	def test_closed_purchase_receipt(self):
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import (
			update_purchase_receipt_status,
		)

		item = make_item()

		pr = make_purchase_receipt(item_code=item.name)

		update_purchase_receipt_status(pr.name, "Closed")
		self.assertEqual(frappe.db.get_value("Purchase Receipt", pr.name, "status"), "Closed")

	def test_pr_billing_status(self):
		"""Flow:
		1. PO -> PR1 -> PI
		2. PO -> PI
		3. PO -> PR2.
		"""
		from erpnext.buying.doctype.purchase_order.purchase_order import (
			make_purchase_invoice as make_purchase_invoice_from_po,
		)
		from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order

		po = create_purchase_order()

		pr1 = make_purchase_receipt(po.name)
		pr1.posting_date = today()
		pr1.posting_time = "10:00"
		pr1.get("items")[0].received_qty = 2
		pr1.get("items")[0].qty = 2
		pr1.submit()

		pi1 = make_purchase_invoice(pr1.name)
		pi1.submit()

		pr1.load_from_db()
		self.assertEqual(pr1.per_billed, 100)

		pi2 = make_purchase_invoice_from_po(po.name)
		pi2.get("items")[0].qty = 4
		pi2.submit()

		pr2 = make_purchase_receipt(po.name)
		pr2.posting_date = today()
		pr2.posting_time = "08:00"
		pr2.get("items")[0].received_qty = 5
		pr2.get("items")[0].qty = 5
		pr2.submit()

		pr1.load_from_db()
		self.assertEqual(pr1.get("items")[0].billed_amt, 1000)
		self.assertEqual(pr1.per_billed, 100)
		self.assertEqual(pr1.status, "Completed")

		pr2.load_from_db()
		self.assertEqual(pr2.get("items")[0].billed_amt, 2000)
		self.assertEqual(pr2.per_billed, 80)
		self.assertEqual(pr2.status, "Partly Billed")

		pr2.cancel()
		pi2.reload()
		pi2.cancel()
		pi1.reload()
		pi1.cancel()
		pr1.reload()
		pr1.cancel()
		po.reload()
		po.cancel()

	def test_serial_no_against_purchase_receipt(self):
		item_code = "Test Manual Created Serial No"
		if not frappe.db.exists("Item", item_code):
			make_item(item_code, dict(has_serial_no=1))

		serial_no = ["12903812901"]
		if not frappe.db.exists("Serial No", serial_no[0]):
			frappe.get_doc(
				{"doctype": "Serial No", "item_code": item_code, "serial_no": serial_no[0]}
			).insert()

		pr_doc = make_purchase_receipt(item_code=item_code, qty=1, serial_no=serial_no)
		pr_doc.load_from_db()

		bundle_id = pr_doc.items[0].serial_and_batch_bundle
		self.assertEqual(serial_no[0], get_serial_nos_from_bundle(bundle_id)[0])

		voucher_no = frappe.db.get_value("Serial and Batch Bundle", bundle_id, "voucher_no")

		self.assertEqual(voucher_no, pr_doc.name)
		pr_doc.cancel()

		# check for the auto created serial nos
		item_code = "Test Auto Created Serial No"
		if not frappe.db.exists("Item", item_code):
			make_item(item_code, dict(has_serial_no=1, serial_no_series="KLJL.###"))

		new_pr_doc = make_purchase_receipt(item_code=item_code, qty=1)
		new_pr_doc.load_from_db()

		bundle_id = new_pr_doc.items[0].serial_and_batch_bundle
		serial_no = get_serial_nos_from_bundle(bundle_id)[0]
		self.assertTrue(serial_no)

		voucher_no = frappe.db.get_value("Serial and Batch Bundle", bundle_id, "voucher_no")

		self.assertEqual(voucher_no, new_pr_doc.name)

		new_pr_doc.cancel()

	def test_purchase_receipt_cost_center(self):
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center

		cost_center = "_Test Cost Center for BS Account - TCP1"
		create_cost_center(
			cost_center_name="_Test Cost Center for BS Account",
			company="_Test Company with perpetual inventory",
		)

		if not frappe.db.exists("Location", "Test Location"):
			frappe.get_doc({"doctype": "Location", "location_name": "Test Location"}).insert()

		pr = make_purchase_receipt(
			cost_center=cost_center,
			company="_Test Company with perpetual inventory",
			warehouse="Stores - TCP1",
			supplier_warehouse="Work In Progress - TCP1",
		)

		stock_in_hand_account = get_inventory_account(pr.company, pr.get("items")[0].warehouse)
		gl_entries = get_gl_entries("Purchase Receipt", pr.name)

		self.assertTrue(gl_entries)

		expected_values = {
			"Stock Received But Not Billed - TCP1": {"cost_center": cost_center},
			stock_in_hand_account: {"cost_center": cost_center},
		}
		for _i, gle in enumerate(gl_entries):
			self.assertEqual(expected_values[gle.account]["cost_center"], gle.cost_center)

		pr.cancel()

	def test_purchase_receipt_cost_center_with_balance_sheet_account(self):
		if not frappe.db.exists("Location", "Test Location"):
			frappe.get_doc({"doctype": "Location", "location_name": "Test Location"}).insert()

		pr = make_purchase_receipt(
			company="_Test Company with perpetual inventory",
			warehouse="Stores - TCP1",
			supplier_warehouse="Work In Progress - TCP1",
		)

		stock_in_hand_account = get_inventory_account(pr.company, pr.get("items")[0].warehouse)
		gl_entries = get_gl_entries("Purchase Receipt", pr.name)

		self.assertTrue(gl_entries)
		cost_center = pr.get("items")[0].cost_center

		expected_values = {
			"Stock Received But Not Billed - TCP1": {"cost_center": cost_center},
			stock_in_hand_account: {"cost_center": cost_center},
		}
		for _i, gle in enumerate(gl_entries):
			self.assertEqual(expected_values[gle.account]["cost_center"], gle.cost_center)

		pr.cancel()

	def test_make_purchase_invoice_from_pr_for_returned_qty(self):
		from erpnext.buying.doctype.purchase_order.test_purchase_order import (
			create_pr_against_po,
			create_purchase_order,
		)

		frappe.db.set_single_value("Buying Settings", "bill_for_rejected_quantity_in_purchase_invoice", 0)

		po = create_purchase_order()
		pr = create_pr_against_po(po.name)

		pr1 = make_purchase_receipt(qty=-1, is_return=1, return_against=pr.name, do_not_submit=True)
		pr1.items[0].purchase_order = po.name
		pr1.items[0].purchase_order_item = po.items[0].name
		pr1.items[0].purchase_receipt_item = pr.items[0].name
		pr1.submit()

		pi1 = make_purchase_invoice(pr.name)
		self.assertEqual(pi1.items[0].qty, 3)

		pr1.cancel()
		pr.reload()
		pr.cancel()
		po.reload()
		po.cancel()

	def test_make_purchase_invoice_from_pr_with_returned_qty_duplicate_items(self):
		frappe.db.set_single_value("Buying Settings", "bill_for_rejected_quantity_in_purchase_invoice", 0)
		pr1 = make_purchase_receipt(qty=8, do_not_submit=True)
		pr1.append(
			"items",
			{
				"item_code": "_Test Item",
				"warehouse": "_Test Warehouse - _TC",
				"qty": 1,
				"received_qty": 1,
				"rate": 100,
				"conversion_factor": 1.0,
			},
		)
		pr1.submit()

		pi1 = make_purchase_invoice(pr1.name)
		pi1.items[0].qty = 4
		pi1.items.pop(1)
		pi1.save()
		pi1.submit()

		pr2 = make_purchase_receipt(qty=-2, is_return=1, return_against=pr1.name, do_not_submit=True)
		pr2.items[0].purchase_receipt_item = pr1.items[0].name
		pr2.submit()

		pi2 = make_purchase_invoice(pr1.name)
		self.assertEqual(pi2.items[0].qty, 2)
		self.assertEqual(pi2.items[1].qty, 1)

		pr2.cancel()
		pi1.cancel()
		pr1.reload()
		pr1.cancel()

	def test_stock_transfer_from_purchase_receipt(self):
		from erpnext.stock.doctype.delivery_note.delivery_note import make_inter_company_purchase_receipt
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

		prepare_data_for_internal_transfer()

		customer = "_Test Internal Customer 2"
		company = "_Test Company with perpetual inventory"

		pr1 = make_purchase_receipt(
			warehouse="Stores - TCP1", company="_Test Company with perpetual inventory"
		)

		dn1 = create_delivery_note(
			item_code=pr1.items[0].item_code,
			company=company,
			customer=customer,
			cost_center="Main - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			qty=5,
			rate=500,
			warehouse="Stores - TCP1",
			target_warehouse="Work In Progress - TCP1",
		)

		pr = make_inter_company_purchase_receipt(dn1.name)
		pr.items[0].from_warehouse = "Work In Progress - TCP1"
		pr.items[0].warehouse = "Stores - TCP1"
		pr.submit()

		gl_entries = get_gl_entries("Purchase Receipt", pr.name)
		sl_entries = get_sl_entries("Purchase Receipt", pr.name)

		self.assertFalse(gl_entries)

		expected_sle = {"Work In Progress - TCP1": -5, "Stores - TCP1": 5}

		for sle in sl_entries:
			self.assertEqual(expected_sle[sle.warehouse], sle.actual_qty)

		pr.cancel()

	def test_stock_transfer_from_purchase_receipt_with_valuation(self):
		from erpnext.stock.doctype.delivery_note.delivery_note import make_inter_company_purchase_receipt
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

		prepare_data_for_internal_transfer()

		create_warehouse(
			"_Test Warehouse for Valuation",
			company="_Test Company with perpetual inventory",
			properties={"account": "_Test Account Stock In Hand - TCP1"},
		)

		pr1 = make_purchase_receipt(
			warehouse="Stores - TCP1",
			company="_Test Company with perpetual inventory",
		)

		customer = "_Test Internal Customer 2"
		company = "_Test Company with perpetual inventory"

		dn1 = create_delivery_note(
			item_code=pr1.items[0].item_code,
			company=company,
			customer=customer,
			cost_center="Main - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			qty=5,
			rate=50,
			warehouse="Stores - TCP1",
			target_warehouse="_Test Warehouse for Valuation - TCP1",
		)

		pr = make_inter_company_purchase_receipt(dn1.name)
		pr.items[0].from_warehouse = "_Test Warehouse for Valuation - TCP1"
		pr.items[0].warehouse = "Stores - TCP1"

		pr.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": "_Test Account Shipping Charges - TCP1",
				"category": "Valuation and Total",
				"cost_center": "Main - TCP1",
				"description": "Test",
				"rate": 9,
			},
		)

		pr.submit()
		gl_entries = get_gl_entries("Purchase Receipt", pr.name)
		sl_entries = get_sl_entries("Purchase Receipt", pr.name)

		if frappe.db.db_type == "postgres":
			expected_gle = [
				["_Test Account Stock In Hand - TCP1", 0.0, 250.0],
				["_Test Account Shipping Charges - TCP1", 0.0, 22.5],
				["Stock In Hand - TCP1", 272.5, 0.0],
				["Cost of Goods Sold - TCP1", 22.5, 0.0],
			]
		else:
			expected_gle = [
				["Stock In Hand - TCP1", 272.5, 0.0],
				["_Test Account Stock In Hand - TCP1", 0.0, 250.0],
				["_Test Account Shipping Charges - TCP1", 0.0, 22.5],
			]

		expected_sle = {"_Test Warehouse for Valuation - TCP1": -5, "Stores - TCP1": 5}

		for sle in sl_entries:
			self.assertEqual(expected_sle[sle.warehouse], sle.actual_qty)

		for i, gle in enumerate(gl_entries):
			self.assertEqual(gle.account, expected_gle[i][0])
			self.assertEqual(gle.debit, expected_gle[i][1])
			self.assertEqual(gle.credit, expected_gle[i][2])

		pr.cancel()

	def test_po_to_pi_and_po_to_pr_worflow_full(self):
		"""Test following behaviour:
		- Create PO
		- Create PI from PO and submit
		- Create PR from PO and submit
		"""
		from erpnext.buying.doctype.purchase_order import purchase_order, test_purchase_order

		po = test_purchase_order.create_purchase_order()

		pi = purchase_order.make_purchase_invoice(po.name)
		pi.submit()

		pr = purchase_order.make_purchase_receipt(po.name)
		pr.submit()

		pr.load_from_db()

		self.assertEqual(pr.status, "Completed")
		self.assertEqual(pr.per_billed, 100)

	def test_po_to_pi_and_po_to_pr_worflow_partial(self):
		"""Test following behaviour:
		- Create PO
		- Create partial PI from PO and submit
		- Create PR from PO and submit
		"""
		from erpnext.buying.doctype.purchase_order import purchase_order, test_purchase_order

		po = test_purchase_order.create_purchase_order()

		pi = purchase_order.make_purchase_invoice(po.name)
		pi.items[0].qty /= 2  # roughly 50%, ^ this function only creates PI with 1 item.
		pi.submit()

		pr = purchase_order.make_purchase_receipt(po.name)
		pr.save()
		# per_billed is only updated after submission.
		self.assertEqual(flt(pr.per_billed), 0)

		pr.submit()

		pi.load_from_db()
		pr.load_from_db()

		self.assertEqual(pr.status, "Partly Billed")
		self.assertAlmostEqual(pr.per_billed, 50.0, places=2)

	def test_purchase_receipt_with_exchange_rate_difference(self):
		from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import (
			make_purchase_receipt as create_purchase_receipt,
		)
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import (
			make_purchase_invoice as create_purchase_invoice,
		)
		from erpnext.accounts.party import add_party_account

		add_party_account(
			"Supplier",
			"_Test Supplier USD",
			"_Test Company with perpetual inventory",
			"_Test Payable USD - TCP1",
		)

		pi = create_purchase_invoice(
			company="_Test Company with perpetual inventory",
			cost_center="Main - TCP1",
			warehouse="Stores - TCP1",
			expense_account="_Test Account Cost for Goods Sold - TCP1",
			currency="USD",
			conversion_rate=70,
			supplier="_Test Supplier USD",
		)

		pr = create_purchase_receipt(pi.name)
		pr.conversion_rate = 80
		pr.items[0].purchase_invoice = pi.name
		pr.items[0].purchase_invoice_item = pi.items[0].name

		pr.save()
		pr.submit()

		# Get exchnage gain and loss account
		exchange_gain_loss_account = frappe.db.get_value("Company", pr.company, "exchange_gain_loss_account")

		# fetching the latest GL Entry with exchange gain and loss account account
		amount = frappe.db.get_value(
			"GL Entry", {"account": exchange_gain_loss_account, "voucher_no": pr.name}, "credit"
		)
		discrepancy_caused_by_exchange_rate_diff = abs(
			pi.items[0].base_net_amount - pr.items[0].base_net_amount
		)

		self.assertEqual(discrepancy_caused_by_exchange_rate_diff, amount)

	def test_payment_terms_are_fetched_when_creating_purchase_invoice(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			create_payment_terms_template,
		)
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
		from erpnext.buying.doctype.purchase_order.test_purchase_order import (
			create_purchase_order,
			make_pr_against_po,
		)
		from erpnext.selling.doctype.sales_order.test_sales_order import (
			automatically_fetch_payment_terms,
			compare_payment_schedules,
		)

		automatically_fetch_payment_terms()

		po = create_purchase_order(qty=10, rate=100, do_not_save=1)
		create_payment_terms_template()
		po.payment_terms_template = "Test Receivable Template"
		po.submit()

		pr = make_pr_against_po(po.name, received_qty=10)

		pi = make_purchase_invoice(qty=10, rate=100, do_not_save=1)
		pi.items[0].purchase_receipt = pr.name
		pi.items[0].pr_detail = pr.items[0].name
		pi.items[0].purchase_order = po.name
		pi.items[0].po_detail = po.items[0].name
		pi.insert(ignore_permissions=True)

		# self.assertEqual(po.payment_terms_template, pi.payment_terms_template)
		compare_payment_schedules(self, po, pi)

		automatically_fetch_payment_terms(enable=0)

	@change_settings("Stock Settings", {"allow_negative_stock": 1})
	def test_neg_to_positive(self):
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		item_code = "_TestNegToPosItem"
		warehouse = "Stores - TCP1"
		company = "_Test Company with perpetual inventory"
		account = "Stock Received But Not Billed - TCP1"

		make_item(item_code)
		se = make_stock_entry(item_code=item_code, from_warehouse=warehouse, qty=50, do_not_save=True, rate=0)
		se.items[0].allow_zero_valuation_rate = 1
		se.save()
		se.submit()

		pr = make_purchase_receipt(
			qty=50,
			rate=1,
			item_code=item_code,
			warehouse=warehouse,
			get_taxes_and_charges=True,
			company=company,
		)
		gles = get_gl_entries(pr.doctype, pr.name)

		for gle in gles:
			if gle.account == account:
				self.assertEqual(gle.credit, 50)

	def test_backdated_transaction_for_internal_transfer(self):
		from erpnext.stock.doctype.delivery_note.delivery_note import make_inter_company_purchase_receipt
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

		prepare_data_for_internal_transfer()
		customer = "_Test Internal Customer 2"
		company = "_Test Company with perpetual inventory"

		from_warehouse = create_warehouse("_Test Internal From Warehouse New", company=company)
		to_warehouse = create_warehouse("_Test Internal To Warehouse New", company=company)
		item_doc = create_item("Test Internal Transfer Item")

		target_warehouse = create_warehouse("_Test Internal GIT Warehouse New", company=company)

		make_purchase_receipt(
			item_code=item_doc.name,
			company=company,
			posting_date=add_days(today(), -1),
			warehouse=from_warehouse,
			qty=1,
			rate=100,
		)

		dn1 = create_delivery_note(
			item_code=item_doc.name,
			company=company,
			customer=customer,
			cost_center="Main - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			qty=1,
			rate=500,
			warehouse=from_warehouse,
			target_warehouse=target_warehouse,
		)

		self.assertEqual(dn1.items[0].rate, 100)

		pr1 = make_inter_company_purchase_receipt(dn1.name)
		pr1.items[0].warehouse = to_warehouse
		self.assertEqual(pr1.items[0].rate, 100)
		pr1.submit()

		self.assertEqual(pr1.is_internal_supplier, 1)

		# Backdated purchase receipt entry, the valuation rate should be updated for DN1 and PR1
		make_purchase_receipt(
			item_code=item_doc.name,
			company=company,
			posting_date=add_days(today(), -2),
			warehouse=from_warehouse,
			qty=1,
			rate=200,
		)

		dn_value = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": "Delivery Note", "voucher_no": dn1.name, "warehouse": target_warehouse},
			"stock_value_difference",
		)

		self.assertEqual(abs(dn_value), 200.00)

		pr_value = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": pr1.name, "warehouse": to_warehouse},
			"stock_value_difference",
		)

		self.assertEqual(abs(pr_value), 200.00)
		pr1.load_from_db()

		self.assertEqual(pr1.items[0].valuation_rate, 200)
		self.assertEqual(pr1.items[0].rate, 100)

		Gl = frappe.qb.DocType("GL Entry")

		query = (
			frappe.qb.from_(Gl)
			.select(
				(fn.Sum(Gl.debit) - fn.Sum(Gl.credit)).as_("value"),
			)
			.where((Gl.voucher_type == pr1.doctype) & (Gl.voucher_no == pr1.name))
		).run(as_dict=True)

		self.assertEqual(query[0].value, 0)

	def test_backdated_transaction_for_internal_transfer_in_trasit_warehouse_for_purchase_receipt(
		self,
	):
		from erpnext.stock.doctype.delivery_note.delivery_note import make_inter_company_purchase_receipt
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

		prepare_data_for_internal_transfer()
		customer = "_Test Internal Customer 2"
		company = "_Test Company with perpetual inventory"

		from_warehouse = create_warehouse("_Test Internal From Warehouse New", company=company)
		to_warehouse = create_warehouse("_Test Internal To Warehouse New", company=company)
		item_doc = create_item("Test Internal Transfer Item")

		target_warehouse = create_warehouse("_Test Internal GIT Warehouse New", company=company)

		make_purchase_receipt(
			item_code=item_doc.name,
			company=company,
			posting_date=add_days(today(), -1),
			warehouse=from_warehouse,
			qty=1,
			rate=100,
		)

		# Keep stock in advance and make sure that systen won't pick this stock while reposting backdated transaction
		for i in range(1, 4):
			make_purchase_receipt(
				item_code=item_doc.name,
				company=company,
				posting_date=add_days(today(), -1 * i),
				warehouse=target_warehouse,
				qty=1,
				rate=320 * i,
			)

		dn1 = create_delivery_note(
			item_code=item_doc.name,
			company=company,
			customer=customer,
			cost_center="Main - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			qty=1,
			rate=500,
			warehouse=from_warehouse,
			target_warehouse=target_warehouse,
		)

		self.assertEqual(dn1.items[0].rate, 100)

		pr1 = make_inter_company_purchase_receipt(dn1.name)
		pr1.items[0].warehouse = to_warehouse
		self.assertEqual(pr1.items[0].rate, 100)
		pr1.submit()

		stk_ledger = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": pr1.name, "warehouse": target_warehouse},
			["stock_value_difference", "outgoing_rate"],
			as_dict=True,
		)

		self.assertEqual(abs(stk_ledger.stock_value_difference), 100)
		self.assertEqual(stk_ledger.outgoing_rate, 100)

		# Backdated purchase receipt entry, the valuation rate should be updated for DN1 and PR1
		make_purchase_receipt(
			item_code=item_doc.name,
			company=company,
			posting_date=add_days(today(), -2),
			warehouse=from_warehouse,
			qty=1,
			rate=200,
		)

		dn_value = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": "Delivery Note", "voucher_no": dn1.name, "warehouse": target_warehouse},
			"stock_value_difference",
		)

		self.assertEqual(abs(dn_value), 200.00)

		pr_value = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": pr1.name, "warehouse": to_warehouse},
			"stock_value_difference",
		)

		self.assertEqual(abs(pr_value), 200.00)
		pr1.load_from_db()

		self.assertEqual(pr1.items[0].valuation_rate, 200)
		self.assertEqual(pr1.items[0].rate, 100)

		Gl = frappe.qb.DocType("GL Entry")

		query = (
			frappe.qb.from_(Gl)
			.select(
				(fn.Sum(Gl.debit) - fn.Sum(Gl.credit)).as_("value"),
			)
			.where((Gl.voucher_type == pr1.doctype) & (Gl.voucher_no == pr1.name))
		).run(as_dict=True)

		self.assertEqual(query[0].value, 0)

	def test_backdated_transaction_for_internal_transfer_in_trasit_warehouse_for_purchase_invoice(
		self,
	):
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import (
			make_purchase_invoice as make_purchase_invoice_for_si,
		)
		from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
			make_inter_company_purchase_invoice,
		)
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice

		prepare_data_for_internal_transfer()
		customer = "_Test Internal Customer 2"
		company = "_Test Company with perpetual inventory"

		from_warehouse = create_warehouse("_Test Internal From Warehouse New", company=company)
		to_warehouse = create_warehouse("_Test Internal To Warehouse New", company=company)
		item_doc = create_item("Test Internal Transfer Item")

		target_warehouse = create_warehouse("_Test Internal GIT Warehouse New", company=company)

		make_purchase_invoice_for_si(
			item_code=item_doc.name,
			company=company,
			posting_date=add_days(today(), -1),
			warehouse=from_warehouse,
			qty=1,
			update_stock=1,
			expense_account="Cost of Goods Sold - TCP1",
			cost_center="Main - TCP1",
			rate=100,
		)

		# Keep stock in advance and make sure that systen won't pick this stock while reposting backdated transaction
		for i in range(1, 4):
			make_purchase_invoice_for_si(
				item_code=item_doc.name,
				company=company,
				posting_date=add_days(today(), -1 * i),
				warehouse=target_warehouse,
				update_stock=1,
				qty=1,
				expense_account="Cost of Goods Sold - TCP1",
				cost_center="Main - TCP1",
				rate=320 * i,
			)

		si1 = create_sales_invoice(
			item_code=item_doc.name,
			company=company,
			customer=customer,
			cost_center="Main - TCP1",
			income_account="Sales - TCP1",
			qty=1,
			rate=500,
			update_stock=1,
			warehouse=from_warehouse,
			target_warehouse=target_warehouse,
		)

		self.assertEqual(si1.items[0].rate, 100)

		pi1 = make_inter_company_purchase_invoice(si1.name)
		pi1.items[0].warehouse = to_warehouse
		self.assertEqual(pi1.items[0].rate, 100)
		pi1.update_stock = 1
		pi1.save()
		pi1.submit()

		stk_ledger = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": pi1.doctype, "voucher_no": pi1.name, "warehouse": target_warehouse},
			["stock_value_difference", "outgoing_rate"],
			as_dict=True,
		)

		self.assertEqual(abs(stk_ledger.stock_value_difference), 100)
		self.assertEqual(stk_ledger.outgoing_rate, 100)

		# Backdated purchase receipt entry, the valuation rate should be updated for si1 and pi1
		make_purchase_receipt(
			item_code=item_doc.name,
			company=company,
			posting_date=add_days(today(), -2),
			warehouse=from_warehouse,
			qty=1,
			rate=200,
		)

		si_value = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": si1.doctype, "voucher_no": si1.name, "warehouse": target_warehouse},
			"stock_value_difference",
		)

		self.assertEqual(abs(si_value), 200.00)

		pi_value = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": pi1.doctype, "voucher_no": pi1.name, "warehouse": to_warehouse},
			"stock_value_difference",
		)

		self.assertEqual(abs(pi_value), 200.00)
		pi1.load_from_db()

		self.assertEqual(pi1.items[0].valuation_rate, 200)
		self.assertEqual(pi1.items[0].rate, 100)

		Gl = frappe.qb.DocType("GL Entry")

		query = (
			frappe.qb.from_(Gl)
			.select(
				(fn.Sum(Gl.debit) - fn.Sum(Gl.credit)).as_("value"),
			)
			.where((Gl.voucher_type == pi1.doctype) & (Gl.voucher_no == pi1.name))
		).run(as_dict=True)

		self.assertEqual(query[0].value, 0)

	def test_batch_expiry_for_purchase_receipt(self):
		from erpnext.controllers.sales_and_purchase_return import make_return_doc

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

		pi = make_purchase_receipt(
			qty=1,
			item_code=item.name,
			update_stock=True,
		)

		pi.load_from_db()
		batch_no = get_batch_from_bundle(pi.items[0].serial_and_batch_bundle)
		self.assertTrue(batch_no)

		frappe.db.set_value("Batch", batch_no, "expiry_date", add_days(today(), -1))

		return_pi = make_return_doc(pi.doctype, pi.name)
		return_pi.save().submit()

		self.assertTrue(return_pi.docstatus == 1)

	def test_disable_last_purchase_rate(self):
		from erpnext.stock.get_item_details import get_item_details

		item = make_item(
			"_Test Disable Last Purchase Rate",
			{"is_purchase_item": 1, "is_stock_item": 1},
		)

		frappe.db.set_single_value("Buying Settings", "disable_last_purchase_rate", 1)

		pr = make_purchase_receipt(
			qty=1,
			rate=100,
			item_code=item.name,
		)

		args = pr.items[0].as_dict()
		args.update(
			{
				"supplier": pr.supplier,
				"doctype": pr.doctype,
				"conversion_rate": pr.conversion_rate,
				"currency": pr.currency,
				"company": pr.company,
				"posting_date": pr.posting_date,
				"posting_time": pr.posting_time,
			}
		)

		res = get_item_details(args)
		self.assertEqual(res.get("last_purchase_rate"), 0)

		frappe.db.set_single_value("Buying Settings", "disable_last_purchase_rate", 0)

		pr = make_purchase_receipt(
			qty=1,
			rate=100,
			item_code=item.name,
		)

		res = get_item_details(args)
		self.assertEqual(res.get("last_purchase_rate"), 100)

	def test_validate_received_qty_for_internal_pr(self):
		prepare_data_for_internal_transfer()
		customer = "_Test Internal Customer 2"
		company = "_Test Company with perpetual inventory"
		from_warehouse = create_warehouse("_Test Internal From Warehouse New", company=company)
		target_warehouse = create_warehouse("_Test Internal GIT Warehouse New", company=company)
		to_warehouse = create_warehouse("_Test Internal To Warehouse New", company=company)

		# Step 1: Create Item
		item = make_item(properties={"is_stock_item": 1, "valuation_rate": 100})

		# Step 2: Create Stock Entry (Material Receipt)
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		make_stock_entry(
			purpose="Material Receipt",
			item_code=item.name,
			qty=20,
			company=company,
			to_warehouse=from_warehouse,
			posting_date=add_days(today(), -3),
		)

		# Step 3: Create Delivery Note with Internal Customer
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

		dn = create_delivery_note(
			item_code=item.name,
			company=company,
			customer=customer,
			cost_center="Main - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			qty=10,
			rate=100,
			warehouse=from_warehouse,
			target_warehouse=target_warehouse,
		)

		# Step 4: Create Internal Purchase Receipt
		from erpnext.stock.doctype.delivery_note.delivery_note import make_inter_company_purchase_receipt

		pr = make_inter_company_purchase_receipt(dn.name)
		pr.set_posting_time = 1
		pr.posting_date = today()
		pr.items[0].qty = 15
		pr.items[0].from_warehouse = target_warehouse
		pr.items[0].warehouse = to_warehouse
		pr.items[0].rejected_warehouse = from_warehouse
		pr.save()

		self.assertRaises(frappe.ValidationError, pr.submit)

		# Step 5: Test Over Receipt Allowance
		frappe.db.set_single_value("Stock Settings", "over_delivery_receipt_allowance", 50)

		make_stock_entry(
			purpose="Material Transfer",
			item_code=item.name,
			qty=5,
			company=company,
			from_warehouse=from_warehouse,
			to_warehouse=target_warehouse,
			posting_date=add_days(pr.posting_date, -1),
		)

		pr.reload()
		pr.submit()

		frappe.db.set_single_value("Stock Settings", "over_delivery_receipt_allowance", 0)

	def test_internal_pr_gl_entries(self):
		from erpnext.stock.doctype.delivery_note.delivery_note import make_inter_company_purchase_receipt
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
		from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
			create_stock_reconciliation,
		)

		prepare_data_for_internal_transfer()
		customer = "_Test Internal Customer 2"
		company = "_Test Company with perpetual inventory"
		from_warehouse = create_warehouse("_Test Internal From Warehouse New", company=company)
		target_warehouse = create_warehouse("_Test Internal GIT Warehouse New", company=company)
		to_warehouse = create_warehouse("_Test Internal To Warehouse New", company=company)

		item = make_item(properties={"is_stock_item": 1, "valuation_rate": 100})
		make_stock_entry(
			purpose="Material Receipt",
			item_code=item.name,
			qty=10,
			company=company,
			to_warehouse=from_warehouse,
			posting_date=add_days(today(), -3),
		)

		# Step - 1: Create Delivery Note with Internal Customer
		dn = create_delivery_note(
			item_code=item.name,
			company=company,
			customer=customer,
			cost_center="Main - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			qty=10,
			rate=100,
			warehouse=from_warehouse,
			target_warehouse=target_warehouse,
			posting_date=add_days(today(), -2),
		)

		# Step - 2: Create Internal Purchase Receipt
		pr = make_inter_company_purchase_receipt(dn.name)
		pr.items[0].qty = 10
		pr.items[0].from_warehouse = target_warehouse
		pr.items[0].warehouse = to_warehouse
		pr.items[0].rejected_warehouse = from_warehouse
		pr.save()
		pr.submit()

		# Step - 3: Create back-date Stock Reconciliation [After DN and Before PR]
		create_stock_reconciliation(
			item_code=item,
			warehouse=target_warehouse,
			qty=10,
			rate=50,
			company=company,
			posting_date=add_days(today(), -1),
		)

		warehouse_account = get_warehouse_account_map(company)
		stock_account_value = frappe.db.get_value(
			"GL Entry",
			{
				"account": warehouse_account[target_warehouse]["account"],
				"voucher_type": "Purchase Receipt",
				"voucher_no": pr.name,
				"is_cancelled": 0,
			},
			fieldname=["credit"],
		)
		stock_diff = frappe.db.get_all(
			"Stock Ledger Entry",
			filters={
				"voucher_type": "Purchase Receipt",
				"voucher_no": pr.name,
				"is_cancelled": 0,
			},
			fields=["SUM(stock_value_difference) as stock_value_difference"],
		)[0]

		# Value of Stock Account should be equal to the sum of Stock Value Difference
		self.assertEqual(stock_account_value, stock_diff["stock_value_difference"])

	def test_internal_pr_reference(self):
		item = make_item(properties={"is_stock_item": 1, "valuation_rate": 100})
		customer = "_Test Internal Customer 2"
		company = "_Test Company with perpetual inventory"
		from_warehouse = create_warehouse("_Test Internal From Warehouse New 1", company=company)
		target_warehouse = create_warehouse("_Test Internal GIT Warehouse New 1", company=company)
		to_warehouse = create_warehouse("_Test Internal To Warehouse New 1", company=company)

		# Step 2: Create Stock Entry (Material Receipt)
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		make_stock_entry(
			purpose="Material Receipt",
			item_code=item.name,
			qty=15,
			company=company,
			to_warehouse=from_warehouse,
		)

		# Step 3: Create Delivery Note with Internal Customer
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

		dn = create_delivery_note(
			item_code=item.name,
			company=company,
			customer=customer,
			cost_center="Main - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			qty=10,
			rate=100,
			warehouse=from_warehouse,
			target_warehouse=target_warehouse,
		)

		# Step 4: Create Internal Purchase Receipt
		from erpnext.stock.doctype.delivery_note.delivery_note import make_inter_company_purchase_receipt

		pr = make_inter_company_purchase_receipt(dn.name)
		pr.inter_company_reference = ""
		self.assertRaises(frappe.ValidationError, pr.save)

		pr.inter_company_reference = dn.name
		pr.items[0].qty = 10
		pr.items[0].from_warehouse = target_warehouse
		pr.items[0].warehouse = to_warehouse
		pr.items[0].rejected_warehouse = from_warehouse
		pr.save()

		delivery_note_item = pr.items[0].delivery_note_item
		pr.items[0].delivery_note_item = ""

		self.assertRaises(frappe.ValidationError, pr.save)

		pr.load_from_db()
		pr.items[0].delivery_note_item = delivery_note_item
		pr.save()

	def test_purchase_return_valuation_with_rejected_qty(self):
		item_code = "_Test Item Return Valuation"
		create_item(item_code)

		warehouse = create_warehouse("_Test Warehouse Return Valuation")
		rejected_warehouse = create_warehouse("_Test Rejected Warehouse Return Valuation")

		# Step 1: Create Purchase Receipt with valuation rate 100
		make_purchase_receipt(
			item_code=item_code,
			warehouse=warehouse,
			qty=10,
			rate=100,
			rejected_qty=2,
			rejected_warehouse=rejected_warehouse,
		)

		# Step 2: Create One more Purchase Receipt with valuation rate 200
		pr = make_purchase_receipt(
			item_code=item_code,
			warehouse=warehouse,
			qty=10,
			rate=200,
			rejected_qty=2,
			rejected_warehouse=rejected_warehouse,
		)

		# Step 3: Create Purchase Return for 2 qty
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_return

		pr_return = make_purchase_return(pr.name)
		pr_return.items[0].qty = 2 * -1
		pr_return.items[0].received_qty = 2 * -1
		pr_return.items[0].rejected_qty = 0
		pr_return.items[0].rejected_warehouse = ""
		pr_return.save()
		pr_return.submit()

		data = frappe.get_all(
			"Stock Ledger Entry",
			filters={"voucher_no": pr_return.name, "docstatus": 1},
			fields=["SUM(stock_value_difference) as stock_value_difference"],
		)[0]

		self.assertEqual(abs(data["stock_value_difference"]), 400.00)

	def test_return_from_rejected_warehouse(self):
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import (
			make_purchase_return_against_rejected_warehouse,
		)

		item_code = "_Test Item Return from Rejected Warehouse"
		create_item(item_code)

		warehouse = create_warehouse("_Test Warehouse Return Qty Warehouse")
		rejected_warehouse = create_warehouse("_Test Rejected Warehouse Return Qty Warehouse")

		# Step 1: Create Purchase Receipt with valuation rate 100
		pr = make_purchase_receipt(
			item_code=item_code,
			warehouse=warehouse,
			qty=10,
			rate=100,
			rejected_qty=2,
			rejected_warehouse=rejected_warehouse,
			do_not_save=1,
		)

		pr.append(
			"items",
			{"item_code": item_code, "qty": 2, "rate": 100, "warehouse": warehouse, "rejected_qty": 0},
		)
		pr.save()
		pr.submit()
		self.assertEqual(len(pr.items), 2)

		pr_return = make_purchase_return_against_rejected_warehouse(pr.name)
		self.assertEqual(len(pr_return.items), 1)
		self.assertEqual(pr_return.items[0].warehouse, rejected_warehouse)
		self.assertEqual(pr_return.items[0].qty, 2.0 * -1)
		self.assertEqual(pr_return.items[0].rejected_qty, 0.0)
		self.assertEqual(pr_return.items[0].rejected_warehouse, "")

	def test_purchase_receipt_with_backdated_landed_cost_voucher(self):
		from erpnext.controllers.sales_and_purchase_return import make_return_doc
		from erpnext.stock.doctype.landed_cost_voucher.test_landed_cost_voucher import (
			create_landed_cost_voucher,
		)
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		item_code = "_Test Purchase Item With Landed Cost"
		create_item(item_code)

		warehouse = create_warehouse("_Test Purchase Warehouse With Landed Cost")
		warehouse1 = create_warehouse("_Test Purchase Warehouse With Landed Cost 1")
		warehouse2 = create_warehouse("_Test Purchase Warehouse With Landed Cost 2")
		warehouse3 = create_warehouse("_Test Purchase Warehouse With Landed Cost 3")

		pr = make_purchase_receipt(
			item_code=item_code,
			warehouse=warehouse,
			posting_date=add_days(today(), -10),
			posting_time="10:59:59",
			qty=100,
			rate=275.00,
		)

		pr_return = make_return_doc("Purchase Receipt", pr.name)
		pr_return.posting_date = add_days(today(), -9)
		pr_return.items[0].qty = 2 * -1
		pr_return.items[0].received_qty = 2 * -1
		pr_return.submit()

		ste1 = make_stock_entry(
			purpose="Material Transfer",
			posting_date=add_days(today(), -8),
			source=warehouse,
			target=warehouse1,
			item_code=item_code,
			qty=20,
			company=pr.company,
		)

		ste1.reload()
		self.assertEqual(ste1.items[0].valuation_rate, 275.00)

		ste2 = make_stock_entry(
			purpose="Material Transfer",
			posting_date=add_days(today(), -7),
			source=warehouse,
			target=warehouse2,
			item_code=item_code,
			qty=20,
			company=pr.company,
		)

		ste2.reload()
		self.assertEqual(ste2.items[0].valuation_rate, 275.00)

		ste3 = make_stock_entry(
			purpose="Material Transfer",
			posting_date=add_days(today(), -6),
			source=warehouse,
			target=warehouse3,
			item_code=item_code,
			qty=20,
			company=pr.company,
		)

		ste3.reload()
		self.assertEqual(ste3.items[0].valuation_rate, 275.00)

		ste4 = make_stock_entry(
			purpose="Material Transfer",
			posting_date=add_days(today(), -5),
			source=warehouse1,
			target=warehouse,
			item_code=item_code,
			qty=20,
			company=pr.company,
		)

		ste4.reload()
		self.assertEqual(ste4.items[0].valuation_rate, 275.00)

		ste5 = make_stock_entry(
			purpose="Material Transfer",
			posting_date=add_days(today(), -4),
			source=warehouse,
			target=warehouse1,
			item_code=item_code,
			qty=20,
			company=pr.company,
		)

		ste5.reload()
		self.assertEqual(ste5.items[0].valuation_rate, 275.00)

		ste6 = make_stock_entry(
			purpose="Material Transfer",
			posting_date=add_days(today(), -3),
			source=warehouse1,
			target=warehouse,
			item_code=item_code,
			qty=20,
			company=pr.company,
		)

		ste6.reload()
		self.assertEqual(ste6.items[0].valuation_rate, 275.00)

		ste7 = make_stock_entry(
			purpose="Material Transfer",
			posting_date=add_days(today(), -3),
			source=warehouse,
			target=warehouse1,
			item_code=item_code,
			qty=20,
			company=pr.company,
		)

		ste7.reload()
		self.assertEqual(ste7.items[0].valuation_rate, 275.00)

		create_landed_cost_voucher("Purchase Receipt", pr.name, pr.company, charges=2500 * -1)

		pr.reload()
		valuation_rate = pr.items[0].valuation_rate

		ste1.reload()
		self.assertEqual(ste1.items[0].valuation_rate, valuation_rate)

		ste2.reload()
		self.assertEqual(ste2.items[0].valuation_rate, valuation_rate)

		ste3.reload()
		self.assertEqual(ste3.items[0].valuation_rate, valuation_rate)

		ste4.reload()
		self.assertEqual(ste4.items[0].valuation_rate, valuation_rate)

		ste5.reload()
		self.assertEqual(ste5.items[0].valuation_rate, valuation_rate)

		ste6.reload()
		self.assertEqual(ste6.items[0].valuation_rate, valuation_rate)

		ste7.reload()
		self.assertEqual(ste7.items[0].valuation_rate, valuation_rate)

	def test_purchase_receipt_provisional_accounting(self):
		# Step - 1: Create Supplier with Default Currency as USD
		from erpnext.buying.doctype.supplier.test_supplier import create_supplier

		supplier = create_supplier(default_currency="USD")

		# Step - 2: Setup Company for Provisional Accounting
		from erpnext.accounts.doctype.account.test_account import create_account

		provisional_account = create_account(
			account_name="Provision Account",
			parent_account="Current Liabilities - _TC",
			company="_Test Company",
		)
		company = frappe.get_doc("Company", "_Test Company")
		company.enable_provisional_accounting_for_non_stock_items = 1
		company.default_provisional_account = provisional_account
		company.save()

		# Step - 3: Create Non-Stock Item
		item = make_item(properties={"is_stock_item": 0})

		# Step - 4: Create Purchase Receipt
		pr = make_purchase_receipt(
			qty=2,
			item_code=item.name,
			company=company.name,
			supplier=supplier.name,
			currency=supplier.default_currency,
		)

		# Test - 1: Total and Base Total should not be the same as the currency is different
		self.assertNotEqual(flt(pr.total, 2), flt(pr.base_total, 2))
		self.assertEqual(flt(pr.total * pr.conversion_rate, 2), flt(pr.base_total, 2))

		# Test - 2: Sum of Debit or Credit should be equal to Purchase Receipt Base Total
		amount = frappe.db.get_all(
			"GL Entry", {"docstatus": 1, "voucher_no": pr.name}, ["sum(debit) as debit"]
		)[0]
		expected_amount = pr.base_total
		self.assertEqual(amount["debit"], expected_amount)

		company.enable_provisional_accounting_for_non_stock_items = 0
		company.save()

	def test_purchase_return_status_with_debit_note(self):
		pr = make_purchase_receipt(rejected_qty=10, received_qty=10, rate=100, do_not_save=1)
		pr.items[0].qty = 0
		pr.items[0].stock_qty = 0
		pr.submit()

		return_pr = make_purchase_receipt(
			is_return=1,
			return_against=pr.name,
			qty=0,
			rejected_qty=10 * -1,
			received_qty=10 * -1,
			do_not_save=1,
		)
		return_pr.items[0].qty = 0.0
		return_pr.items[0].stock_qty = 0.0
		return_pr.submit()

		self.assertEqual(return_pr.status, "To Bill")

		pi = make_purchase_invoice(return_pr.name)
		pi.submit()

		return_pr.reload()
		self.assertEqual(return_pr.status, "Completed")

	def test_purchase_return_with_zero_rate(self):
		company = "_Test Company with perpetual inventory"

		# Step - 1: Create Item
		item, warehouse = (
			make_item(properties={"is_stock_item": 1, "valuation_method": "Moving Average"}).name,
			"Stores - TCP1",
		)

		# Step - 2: Create Stock Entry (Material Receipt)
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		se = make_stock_entry(
			purpose="Material Receipt",
			item_code=item,
			qty=100,
			basic_rate=100,
			to_warehouse=warehouse,
			company=company,
		)

		# Step - 3: Create Purchase Receipt
		pr = make_purchase_receipt(
			item_code=item,
			qty=5,
			rate=0,
			warehouse=warehouse,
			company=company,
		)

		# Step - 4: Create Purchase Return
		from erpnext.controllers.sales_and_purchase_return import make_return_doc

		pr_return = make_return_doc("Purchase Receipt", pr.name)
		pr_return.save()
		pr_return.submit()

		sl_entries = get_sl_entries(pr_return.doctype, pr_return.name)
		gl_entries = get_gl_entries(pr_return.doctype, pr_return.name)

		# Test - 1: SLE Stock Value Difference should be equal to Qty * Average Rate
		average_rate = ((se.items[0].qty * se.items[0].basic_rate) + (pr.items[0].qty * pr.items[0].rate)) / (
			se.items[0].qty + pr.items[0].qty
		)
		expected_stock_value_difference = pr_return.items[0].qty * average_rate
		self.assertEqual(
			flt(sl_entries[0].stock_value_difference, 2), flt(expected_stock_value_difference, 2)
		)

		# Test - 2: GL Entries should be created for Stock Value Difference
		self.assertEqual(len(gl_entries), 2)

		# Test - 3: SLE Stock Value Difference should be equal to Debit or Credit of GL Entries.
		for entry in gl_entries:
			self.assertEqual(abs(entry.debit + entry.credit), abs(sl_entries[0].stock_value_difference))

	def non_internal_transfer_purchase_receipt(self):
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		pr_doc = make_purchase_receipt(do_not_submit=True)
		warehouse = create_warehouse("Internal Transfer Warehouse", pr_doc.company)
		pr_doc.items[0].db_set("target_warehouse", "warehouse")

		pr_doc.reload()

		self.assertEqual(pr_doc.items[0].from_warehouse, warehouse.name)

		pr_doc.save()
		pr_doc.reload()
		self.assertFalse(pr_doc.items[0].from_warehouse)

	def test_use_serial_batch_fields_for_serial_nos(self):
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
		from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
			create_stock_reconciliation,
		)

		frappe.db.set_single_value(
			"Stock Settings", "do_not_update_serial_batch_on_creation_of_auto_bundle", 0
		)

		item_code = make_item(
			"_Test Use Serial Fields Item Serial Item",
			properties={"has_serial_no": 1, "serial_no_series": "SNU-TSFISI-.#####"},
		).name

		serial_nos = [
			"SNU-TSFISI-000011",
			"SNU-TSFISI-000012",
			"SNU-TSFISI-000013",
			"SNU-TSFISI-000014",
			"SNU-TSFISI-000015",
		]

		pr = make_purchase_receipt(
			item_code=item_code,
			qty=5,
			serial_no="\n".join(serial_nos),
			use_serial_batch_fields=1,
			rate=100,
		)

		self.assertEqual(pr.items[0].use_serial_batch_fields, 1)
		self.assertTrue(pr.items[0].serial_no)
		self.assertTrue(pr.items[0].serial_and_batch_bundle)

		sbb_doc = frappe.get_doc("Serial and Batch Bundle", pr.items[0].serial_and_batch_bundle)

		for row in sbb_doc.entries:
			self.assertTrue(row.serial_no in serial_nos)

		serial_nos.remove("SNU-TSFISI-000015")

		sr = create_stock_reconciliation(
			item_code=item_code,
			serial_no="\n".join(serial_nos),
			qty=4,
			warehouse=pr.items[0].warehouse,
			use_serial_batch_fields=1,
			do_not_submit=True,
		)
		sr.reload()

		serial_nos = get_serial_nos(sr.items[0].current_serial_no)
		self.assertEqual(len(serial_nos), 5)
		self.assertEqual(sr.items[0].current_qty, 5)

		new_serial_nos = get_serial_nos(sr.items[0].serial_no)
		self.assertEqual(len(new_serial_nos), 4)
		self.assertEqual(sr.items[0].qty, 4)
		self.assertEqual(sr.items[0].use_serial_batch_fields, 1)
		self.assertFalse(sr.items[0].current_serial_and_batch_bundle)
		self.assertFalse(sr.items[0].serial_and_batch_bundle)
		self.assertTrue(sr.items[0].current_serial_no)
		sr.submit()

		sr.reload()
		self.assertTrue(sr.items[0].current_serial_and_batch_bundle)
		self.assertTrue(sr.items[0].serial_and_batch_bundle)

		serial_no_status = frappe.db.get_value("Serial No", "SNU-TSFISI-000015", "status")

		self.assertTrue(serial_no_status != "Active")

		dn = create_delivery_note(
			item_code=item_code,
			qty=4,
			serial_no="\n".join(new_serial_nos),
			use_serial_batch_fields=1,
		)

		self.assertTrue(dn.items[0].serial_and_batch_bundle)
		self.assertEqual(dn.items[0].qty, 4)
		doc = frappe.get_doc("Serial and Batch Bundle", dn.items[0].serial_and_batch_bundle)
		for row in doc.entries:
			self.assertTrue(row.serial_no in new_serial_nos)

		for sn in new_serial_nos:
			serial_no_status = frappe.db.get_value("Serial No", sn, "status")
			self.assertTrue(serial_no_status != "Active")

		frappe.db.set_single_value(
			"Stock Settings", "do_not_update_serial_batch_on_creation_of_auto_bundle", 1
		)

	def test_sle_qty_after_transaction(self):
		item = make_item(
			"_Test Item Qty After Transaction",
			properties={"is_stock_item": 1, "valuation_method": "FIFO"},
		).name

		posting_date = today()
		posting_time = nowtime()

		# Step 1: Create Purchase Receipt
		pr = make_purchase_receipt(
			item_code=item,
			qty=1,
			rate=100,
			posting_date=posting_date,
			posting_time=posting_time,
			do_not_save=1,
		)

		for _i in range(9):
			pr.append(
				"items",
				{
					"item_code": item,
					"qty": 1,
					"rate": 100,
					"warehouse": pr.items[0].warehouse,
					"cost_center": pr.items[0].cost_center,
					"expense_account": pr.items[0].expense_account,
					"uom": pr.items[0].uom,
					"stock_uom": pr.items[0].stock_uom,
					"conversion_factor": pr.items[0].conversion_factor,
				},
			)

		self.assertEqual(len(pr.items), 10)
		pr.save()
		pr.submit()

		data = frappe.get_all(
			"Stock Ledger Entry",
			fields=["qty_after_transaction", "creation", "posting_datetime"],
			filters={"voucher_no": pr.name, "is_cancelled": 0},
			order_by="creation",
		)

		for index, d in enumerate(data):
			self.assertEqual(d.qty_after_transaction, 1 + index)

		# Step 2: Create Purchase Receipt
		pr = make_purchase_receipt(
			item_code=item,
			qty=1,
			rate=100,
			posting_date=posting_date,
			posting_time=posting_time,
			do_not_save=1,
		)

		for _i in range(9):
			pr.append(
				"items",
				{
					"item_code": item,
					"qty": 1,
					"rate": 100,
					"warehouse": pr.items[0].warehouse,
					"cost_center": pr.items[0].cost_center,
					"expense_account": pr.items[0].expense_account,
					"uom": pr.items[0].uom,
					"stock_uom": pr.items[0].stock_uom,
					"conversion_factor": pr.items[0].conversion_factor,
				},
			)

		self.assertEqual(len(pr.items), 10)
		pr.save()
		pr.submit()

		data = frappe.get_all(
			"Stock Ledger Entry",
			fields=["qty_after_transaction", "creation", "posting_datetime"],
			filters={"voucher_no": pr.name, "is_cancelled": 0},
			order_by="creation",
		)

		for index, d in enumerate(data):
			self.assertEqual(d.qty_after_transaction, 11 + index)

	def test_auto_set_batch_based_on_bundle(self):
		item_code = make_item(
			"_Test Auto Set Batch Based on Bundle",
			properties={
				"has_batch_no": 1,
				"batch_number_series": "BATCH-BNU-TASBBB-.#####",
				"create_new_batch": 1,
			},
		).name

		frappe.db.set_single_value(
			"Stock Settings", "do_not_update_serial_batch_on_creation_of_auto_bundle", 0
		)

		pr = make_purchase_receipt(
			item_code=item_code,
			qty=5,
			rate=100,
		)

		self.assertTrue(pr.items[0].batch_no)
		batch_no = get_batch_from_bundle(pr.items[0].serial_and_batch_bundle)
		self.assertEqual(pr.items[0].batch_no, batch_no)

		frappe.db.set_single_value(
			"Stock Settings", "do_not_update_serial_batch_on_creation_of_auto_bundle", 1
		)

	def test_pr_billed_amount_against_return_entry(self):
		from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import make_debit_note
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import (
			make_purchase_invoice as make_pi_from_pr,
		)

		# Create a Purchase Receipt and Fully Bill it
		pr = make_purchase_receipt(qty=10)
		pi = make_pi_from_pr(pr.name)
		pi.insert(ignore_permissions=True)
		pi.submit()

		# Debit Note - 50% Qty & enable updating PR billed amount
		pi_return = make_debit_note(pi.name)
		pi_return.items[0].qty = -5
		pi_return.update_billed_amount_in_purchase_receipt = 1
		pi_return.submit()

		# Check if the billed amount reduced
		pr.reload()
		self.assertEqual(pr.per_billed, 50)

		pi_return.reload()
		pi_return.cancel()

		# Debit Note - 50% Qty & disable updating PR billed amount
		pi_return = make_debit_note(pi.name)
		pi_return.items[0].qty = -5
		pi_return.update_billed_amount_in_purchase_receipt = 0
		pi_return.submit()

		# Check if the billed amount stayed the same
		pr.reload()
		self.assertEqual(pr.per_billed, 100)

	def test_purchase_receipt_with_use_serial_batch_field_for_rejected_qty(self):
		batch_item = make_item(
			"_Test Purchase Receipt Batch Item For Rejected Qty",
			properties={"has_batch_no": 1, "create_new_batch": 1, "is_stock_item": 1},
		).name

		serial_item = make_item(
			"_Test Purchase Receipt Serial Item for Rejected Qty",
			properties={"has_serial_no": 1, "is_stock_item": 1},
		).name

		rej_warehouse = create_warehouse("_Test Purchase Warehouse For Rejected Qty")

		batch_no = "BATCH-BNU-TPRBI-0001"
		serial_nos = ["SNU-TPRSI-0001", "SNU-TPRSI-0002", "SNU-TPRSI-0003"]

		if not frappe.db.exists("Batch", batch_no):
			frappe.get_doc(
				{
					"doctype": "Batch",
					"batch_id": batch_no,
					"item": batch_item,
				}
			).insert()

		for serial_no in serial_nos:
			if not frappe.db.exists("Serial No", serial_no):
				frappe.get_doc(
					{
						"doctype": "Serial No",
						"item_code": serial_item,
						"serial_no": serial_no,
					}
				).insert()

		pr = make_purchase_receipt(
			item_code=batch_item,
			received_qty=10,
			qty=8,
			rejected_qty=2,
			rejected_warehouse=rej_warehouse,
			use_serial_batch_fields=1,
			batch_no=batch_no,
			rate=100,
			do_not_submit=1,
		)

		pr.append(
			"items",
			{
				"item_code": serial_item,
				"qty": 2,
				"rate": 100,
				"base_rate": 100,
				"item_name": serial_item,
				"uom": "Nos",
				"stock_uom": "Nos",
				"conversion_factor": 1,
				"rejected_qty": 1,
				"warehouse": pr.items[0].warehouse,
				"rejected_warehouse": rej_warehouse,
				"use_serial_batch_fields": 1,
				"serial_no": "\n".join(serial_nos[:2]),
				"rejected_serial_no": serial_nos[2],
			},
		)

		pr.save()
		pr.submit()

		pr.reload()

		for row in pr.items:
			self.assertTrue(row.serial_and_batch_bundle)
			self.assertTrue(row.rejected_serial_and_batch_bundle)

			if row.item_code == batch_item:
				self.assertEqual(row.batch_no, batch_no)
			else:
				self.assertEqual(row.serial_no, "\n".join(serial_nos[:2]))
				self.assertEqual(row.rejected_serial_no, serial_nos[2])

	def test_internal_transfer_with_serial_batch_items_and_their_valuation(self):
		from erpnext.controllers.sales_and_purchase_return import make_return_doc
		from erpnext.stock.doctype.delivery_note.delivery_note import make_inter_company_purchase_receipt
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

		prepare_data_for_internal_transfer()

		customer = "_Test Internal Customer 2"
		company = "_Test Company with perpetual inventory"

		batch_item_doc = make_item(
			"_Test Batch Item For Stock Transfer",
			{"has_batch_no": 1, "create_new_batch": 1, "batch_number_series": "BT-BIFST-.####"},
		)

		serial_item_doc = make_item(
			"_Test Serial No Item For Stock Transfer",
			{"has_serial_no": 1, "serial_no_series": "BT-BIFST-.####"},
		)

		inward_entry = make_purchase_receipt(
			item_code=batch_item_doc.name,
			qty=10,
			rate=150,
			warehouse="Stores - TCP1",
			company="_Test Company with perpetual inventory",
			use_serial_batch_fields=1,
			do_not_submit=1,
		)

		inward_entry.append(
			"items",
			{
				"item_code": serial_item_doc.name,
				"qty": 15,
				"rate": 250,
				"item_name": serial_item_doc.item_name,
				"conversion_factor": 1.0,
				"uom": serial_item_doc.stock_uom,
				"stock_uom": serial_item_doc.stock_uom,
				"warehouse": "Stores - TCP1",
				"use_serial_batch_fields": 1,
			},
		)

		inward_entry.submit()
		inward_entry.reload()

		for row in inward_entry.items:
			self.assertTrue(row.serial_and_batch_bundle)

		inter_transfer_dn = create_delivery_note(
			item_code=inward_entry.items[0].item_code,
			company=company,
			customer=customer,
			cost_center="Main - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			qty=10,
			rate=500,
			warehouse="Stores - TCP1",
			target_warehouse="Work In Progress - TCP1",
			batch_no=get_batch_from_bundle(inward_entry.items[0].serial_and_batch_bundle),
			use_serial_batch_fields=1,
			do_not_submit=1,
		)

		inter_transfer_dn.append(
			"items",
			{
				"item_code": serial_item_doc.name,
				"qty": 15,
				"rate": 350,
				"item_name": serial_item_doc.item_name,
				"conversion_factor": 1.0,
				"uom": serial_item_doc.stock_uom,
				"stock_uom": serial_item_doc.stock_uom,
				"warehouse": "Stores - TCP1",
				"target_warehouse": "Work In Progress - TCP1",
				"serial_no": "\n".join(
					get_serial_nos_from_bundle(inward_entry.items[1].serial_and_batch_bundle)
				),
				"use_serial_batch_fields": 1,
			},
		)

		inter_transfer_dn.submit()
		inter_transfer_dn.reload()
		for row in inter_transfer_dn.items:
			if row.item_code == batch_item_doc.name:
				self.assertEqual(row.rate, 150.0)
			else:
				self.assertEqual(row.rate, 250.0)

			self.assertTrue(row.serial_and_batch_bundle)

		inter_transfer_pr = make_inter_company_purchase_receipt(inter_transfer_dn.name)
		for row in inter_transfer_pr.items:
			row.from_warehouse = "Work In Progress - TCP1"
			row.warehouse = "Stores - TCP1"
		inter_transfer_pr.submit()

		for row in inter_transfer_pr.items:
			if row.item_code == batch_item_doc.name:
				self.assertEqual(row.rate, 150.0)
			else:
				self.assertEqual(row.rate, 250.0)

			self.assertTrue(row.serial_and_batch_bundle)

		inter_transfer_pr_return = make_return_doc("Purchase Receipt", inter_transfer_pr.name)

		inter_transfer_pr_return.submit()
		inter_transfer_pr_return.reload()
		for row in inter_transfer_pr_return.items:
			self.assertTrue(row.serial_and_batch_bundle)
			if row.item_code == serial_item_doc.name:
				self.assertEqual(row.rate, 250.0)
				serial_nos = get_serial_nos_from_bundle(row.serial_and_batch_bundle)
				for sn in serial_nos:
					serial_no_details = frappe.db.get_value(
						"Serial No", sn, ["status", "warehouse"], as_dict=1
					)
					self.assertTrue(serial_no_details.status == "Active")
					self.assertEqual(serial_no_details.warehouse, "Work In Progress - TCP1")

		inter_transfer_dn_return = make_return_doc("Delivery Note", inter_transfer_dn.name)
		inter_transfer_dn_return.posting_date = today()
		inter_transfer_dn_return.posting_time = nowtime()
		for row in inter_transfer_dn_return.items:
			row.target_warehouse = "Work In Progress - TCP1"

		inter_transfer_dn_return.submit()
		inter_transfer_dn_return.reload()

		for row in inter_transfer_dn_return.items:
			self.assertTrue(row.serial_and_batch_bundle)

	def test_internal_transfer_with_serial_batch_items_without_use_serial_batch_fields(self):
		from erpnext.controllers.sales_and_purchase_return import make_return_doc
		from erpnext.stock.doctype.delivery_note.delivery_note import make_inter_company_purchase_receipt
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

		frappe.db.set_single_value("Stock Settings", "use_serial_batch_fields", 0)

		prepare_data_for_internal_transfer()

		customer = "_Test Internal Customer 2"
		company = "_Test Company with perpetual inventory"

		batch_item_doc = make_item(
			"_Test Batch Item For Stock Transfer USE SERIAL BATCH FIELDS",
			{"has_batch_no": 1, "create_new_batch": 1, "batch_number_series": "USBF-BT-BIFST-.####"},
		)

		serial_item_doc = make_item(
			"_Test Serial No Item For Stock Transfer USE SERIAL BATCH FIELDS",
			{"has_serial_no": 1, "serial_no_series": "USBF-BT-BIFST-.####"},
		)

		inward_entry = make_purchase_receipt(
			item_code=batch_item_doc.name,
			qty=10,
			rate=150,
			warehouse="Stores - TCP1",
			company="_Test Company with perpetual inventory",
			use_serial_batch_fields=0,
			do_not_submit=1,
		)

		inward_entry.append(
			"items",
			{
				"item_code": serial_item_doc.name,
				"qty": 15,
				"rate": 250,
				"item_name": serial_item_doc.item_name,
				"conversion_factor": 1.0,
				"uom": serial_item_doc.stock_uom,
				"stock_uom": serial_item_doc.stock_uom,
				"warehouse": "Stores - TCP1",
				"use_serial_batch_fields": 0,
			},
		)

		inward_entry.submit()
		inward_entry.reload()

		for row in inward_entry.items:
			self.assertTrue(row.serial_and_batch_bundle)

		inter_transfer_dn = create_delivery_note(
			item_code=inward_entry.items[0].item_code,
			company=company,
			customer=customer,
			cost_center="Main - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			qty=10,
			rate=500,
			warehouse="Stores - TCP1",
			target_warehouse="Work In Progress - TCP1",
			batch_no=get_batch_from_bundle(inward_entry.items[0].serial_and_batch_bundle),
			use_serial_batch_fields=0,
			do_not_submit=1,
		)

		inter_transfer_dn.append(
			"items",
			{
				"item_code": serial_item_doc.name,
				"qty": 15,
				"rate": 350,
				"item_name": serial_item_doc.item_name,
				"conversion_factor": 1.0,
				"uom": serial_item_doc.stock_uom,
				"stock_uom": serial_item_doc.stock_uom,
				"warehouse": "Stores - TCP1",
				"target_warehouse": "Work In Progress - TCP1",
				"serial_no": "\n".join(
					get_serial_nos_from_bundle(inward_entry.items[1].serial_and_batch_bundle)
				),
				"use_serial_batch_fields": 0,
			},
		)

		inter_transfer_dn.submit()
		inter_transfer_dn.reload()
		for row in inter_transfer_dn.items:
			if row.item_code == batch_item_doc.name:
				self.assertEqual(row.rate, 150.0)
			else:
				self.assertEqual(row.rate, 250.0)

			self.assertTrue(row.serial_and_batch_bundle)

		inter_transfer_pr = make_inter_company_purchase_receipt(inter_transfer_dn.name)
		for row in inter_transfer_pr.items:
			row.from_warehouse = "Work In Progress - TCP1"
			row.warehouse = "Stores - TCP1"
		inter_transfer_pr.submit()

		for row in inter_transfer_pr.items:
			if row.item_code == batch_item_doc.name:
				self.assertEqual(row.rate, 150.0)
			else:
				self.assertEqual(row.rate, 250.0)

			self.assertTrue(row.serial_and_batch_bundle)

		inter_transfer_pr_return = make_return_doc("Purchase Receipt", inter_transfer_pr.name)

		inter_transfer_pr_return.submit()
		inter_transfer_pr_return.reload()
		for row in inter_transfer_pr_return.items:
			self.assertTrue(row.serial_and_batch_bundle)
			if row.item_code == serial_item_doc.name:
				self.assertEqual(row.rate, 250.0)
				serial_nos = get_serial_nos_from_bundle(row.serial_and_batch_bundle)
				for sn in serial_nos:
					serial_no_details = frappe.db.get_value(
						"Serial No", sn, ["status", "warehouse"], as_dict=1
					)
					self.assertTrue(serial_no_details.status == "Active")
					self.assertEqual(serial_no_details.warehouse, "Work In Progress - TCP1")

		inter_transfer_dn_return = make_return_doc("Delivery Note", inter_transfer_dn.name)
		inter_transfer_dn_return.posting_date = today()
		inter_transfer_dn_return.posting_time = nowtime()
		for row in inter_transfer_dn_return.items:
			row.target_warehouse = "Work In Progress - TCP1"

		inter_transfer_dn_return.submit()
		inter_transfer_dn_return.reload()

		for row in inter_transfer_dn_return.items:
			self.assertTrue(row.serial_and_batch_bundle)

		frappe.db.set_single_value("Stock Settings", "use_serial_batch_fields", 1)

	def test_purchase_receipt_bill_for_rejected_quantity_in_purchase_invoice(self):
		item_code = make_item(
			"_Test Purchase Receipt Bill For Rejected Quantity",
			properties={"is_stock_item": 1},
		).name

		pr = make_purchase_receipt(item_code=item_code, qty=5, rate=100)

		return_pr = make_purchase_receipt(
			item_code=item_code,
			is_return=1,
			return_against=pr.name,
			qty=-2,
			do_not_submit=1,
		)
		return_pr.items[0].purchase_receipt_item = pr.items[0].name
		return_pr.submit()
		old_value = frappe.db.get_single_value(
			"Buying Settings", "bill_for_rejected_quantity_in_purchase_invoice"
		)

		frappe.db.set_single_value("Buying Settings", "bill_for_rejected_quantity_in_purchase_invoice", 0)
		pi = make_purchase_invoice(pr.name)
		self.assertEqual(pi.items[0].qty, 3)

		frappe.db.set_single_value("Buying Settings", "bill_for_rejected_quantity_in_purchase_invoice", 1)
		pi = make_purchase_invoice(pr.name)
		pi.submit()
		self.assertEqual(pi.items[0].qty, 5)

		frappe.db.set_single_value(
			"Buying Settings", "bill_for_rejected_quantity_in_purchase_invoice", old_value
		)

	def test_zero_valuation_rate_for_batched_item(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		item = make_item(
			"_Test Zero Valuation Rate For the Batch Item",
			{
				"is_purchase_item": 1,
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "TZVRFORBATCH.#####",
				"valuation_rate": 200,
			},
		)

		pi = make_purchase_receipt(
			qty=10,
			rate=0,
			item_code=item.name,
		)

		pi.reload()
		batch_no = get_batch_from_bundle(pi.items[0].serial_and_batch_bundle)

		se = make_stock_entry(
			purpose="Material Issue",
			item_code=item.name,
			source=pi.items[0].warehouse,
			qty=10,
			batch_no=batch_no,
			use_serial_batch_fields=0,
		)

		se.submit()

		se.reload()

		self.assertEqual(se.items[0].valuation_rate, 0)
		self.assertEqual(se.items[0].basic_rate, 0)

		sabb_doc = frappe.get_doc("Serial and Batch Bundle", se.items[0].serial_and_batch_bundle)
		for row in sabb_doc.entries:
			self.assertEqual(row.incoming_rate, 0)

	def test_purchase_return_from_accepted_and_rejected_warehouse(self):
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import (
			make_purchase_return,
		)

		item = make_item(
			"_Test PR Item With Return From Accepted and Rejected WH",
			{
				"is_purchase_item": 1,
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "SD-TZVRFORBATCH.#####",
				"valuation_rate": 200,
			},
		)

		pr = make_purchase_receipt(
			qty=10,
			rejected_qty=5,
			rate=100,
			item_code=item.name,
		)

		pr.reload()
		self.assertTrue(pr.items[0].serial_and_batch_bundle)
		self.assertTrue(pr.items[0].rejected_serial_and_batch_bundle)

		return_pr = make_purchase_return(pr.name)
		return_pr.submit()

		return_pr.reload()
		self.assertTrue(return_pr.items[0].serial_and_batch_bundle)
		self.assertTrue(return_pr.items[0].rejected_serial_and_batch_bundle)

		self.assertEqual(
			return_pr.items[0].qty,
			frappe.db.get_value(
				"Serial and Batch Bundle", return_pr.items[0].serial_and_batch_bundle, "total_qty"
			),
		)

		self.assertEqual(
			return_pr.items[0].rejected_qty,
			frappe.db.get_value(
				"Serial and Batch Bundle", return_pr.items[0].rejected_serial_and_batch_bundle, "total_qty"
			),
		)

	def test_valuation_taxes_lcv_repost_after_billing(self):
		from erpnext.stock.doctype.landed_cost_voucher.test_landed_cost_voucher import (
			make_landed_cost_voucher,
		)

		old_perpetual_inventory = erpnext.is_perpetual_inventory_enabled("_Test Company")
		frappe.local.enable_perpetual_inventory["_Test Company"] = 1
		frappe.db.set_value(
			"Company",
			"_Test Company",
			"stock_received_but_not_billed",
			"Stock Received But Not Billed - _TC",
		)

		pr = make_purchase_receipt(qty=10, rate=1000, do_not_submit=1)
		pr.append(
			"taxes",
			{
				"category": "Valuation and Total",
				"charge_type": "Actual",
				"account_head": "Freight and Forwarding Charges - _TC",
				"tax_amount": 2000,
				"description": "Test",
			},
		)
		pr.submit()
		pi = make_purchase_invoice(pr.name)
		pi.submit()
		make_landed_cost_voucher(
			company=pr.company,
			receipt_document_type="Purchase Receipt",
			receipt_document=pr.name,
			charges=2000,
			distribute_charges_based_on="Qty",
			expense_account="Expenses Included In Valuation - _TC",
		)

		gl_entries = get_gl_entries("Purchase Receipt", pr.name, skip_cancelled=True, as_dict=False)
		warehouse_account = get_warehouse_account_map("_Test Company")
		if frappe.db.db_type == "postgres":
			expected_gle = (
				(warehouse_account[pr.items[0].warehouse]["account"], 14000, 0, "Main - _TC"),
				("Stock Received But Not Billed - _TC", 0, 10000, "Main - _TC"),
				("Freight and Forwarding Charges - _TC", 0, 2000, "Main - _TC"),
				("Expenses Included In Valuation - _TC", 0, 2000, "Main - _TC"),
			)
		else:
			expected_gle = (
				("Stock Received But Not Billed - _TC", 0, 10000, "Main - _TC"),
				("Freight and Forwarding Charges - _TC", 0, 2000, "Main - _TC"),
				("Expenses Included In Valuation - _TC", 0, 2000, "Main - _TC"),
				(warehouse_account[pr.items[0].warehouse]["account"], 14000, 0, "Main - _TC"),
			)
		self.assertSequenceEqual(expected_gle, gl_entries)
		frappe.local.enable_perpetual_inventory["_Test Company"] = old_perpetual_inventory

	def test_manufacturing_and_expiry_date_for_batch(self):
		item = make_item(
			"_Test Manufacturing and Expiry Date For Batch",
			{
				"is_purchase_item": 1,
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "B-MEBATCH.#####",
				"has_expiry_date": 1,
				"shelf_life_in_days": 5,
			},
		)

		pr = make_purchase_receipt(
			qty=10,
			rate=100,
			item_code=item.name,
			posting_date=today(),
		)

		pr.reload()
		self.assertTrue(pr.items[0].serial_and_batch_bundle)

		batch_no = get_batch_from_bundle(pr.items[0].serial_and_batch_bundle)
		batch = frappe.get_doc("Batch", batch_no)
		self.assertEqual(batch.manufacturing_date, getdate(today()))
		self.assertEqual(batch.expiry_date, getdate(add_days(today(), 5)))

	def test_purchase_return_from_rejected_warehouse(self):
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import (
			make_purchase_return_against_rejected_warehouse,
		)

		item_code = "_Test Item Return from Rejected Warehouse 11"
		create_item(item_code)

		warehouse = create_warehouse("_Test Warehouse Return Qty Warehouse 11")
		rejected_warehouse = create_warehouse("_Test Rejected Warehouse Return Qty Warehouse 11")

		# Step 1: Create Purchase Receipt with valuation rate 100
		pr = make_purchase_receipt(
			item_code=item_code,
			warehouse=warehouse,
			qty=24,
			rate=100,
			rejected_qty=31,
			rejected_warehouse=rejected_warehouse,
		)

		pr_return = make_purchase_return_against_rejected_warehouse(pr.name)
		pr_return.save()
		pr_return.submit()

		self.assertEqual(pr_return.items[0].warehouse, rejected_warehouse)
		self.assertEqual(pr_return.items[0].qty, 31 * -1)
		self.assertEqual(pr_return.items[0].rejected_qty, 0.0)
		self.assertEqual(pr_return.items[0].rejected_warehouse, "")

	def test_tax_account_heads_on_lcv_and_item_repost(self):
		"""
		PO -> PR -> PI
		PR -> LCV
		Backdated `Repost Item valuation` should not merge tax account heads into stock_rbnb
		"""
		from erpnext.accounts.doctype.account.test_account import create_account
		from erpnext.buying.doctype.purchase_order.test_purchase_order import (
			create_purchase_order,
			make_pr_against_po,
		)
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice

		stock_rbnb = "Stock Received But Not Billed - _TC"
		stock_in_hand = "Stock In Hand - _TC"
		test_cc = "_Test Cost Center - _TC"
		test_company = "_Test Company"
		creditors = "Creditors - _TC"
		lcv_expense_account = "Expenses Included In Valuation - _TC"

		company_doc = frappe.get_doc("Company", test_company)
		company_doc.enable_perpetual_inventory = True
		company_doc.stock_received_but_not_billed = stock_rbnb
		company_doc.default_inventory_account = stock_in_hand
		company_doc.save()

		packaging_charges_account = create_account(
			account_name="Packaging Charges",
			parent_account="Indirect Expenses - _TC",
			company=test_company,
			account_type="Tax",
		)

		po = create_purchase_order(qty=10, rate=100, do_not_save=1)
		po.taxes = []
		po.append(
			"taxes",
			{
				"category": "Valuation and Total",
				"account_head": packaging_charges_account,
				"cost_center": test_cc,
				"description": "Test",
				"add_deduct_tax": "Add",
				"charge_type": "Actual",
				"tax_amount": 250,
			},
		)
		po.save().submit()

		pr = make_pr_against_po(po.name, received_qty=10)
		pr_gl_entries = get_gl_entries(pr.doctype, pr.name, skip_cancelled=True)
		expected_pr_gles = [
			{"account": stock_rbnb, "debit": 0.0, "credit": 1000.0, "cost_center": test_cc},
			{"account": stock_in_hand, "debit": 1250.0, "credit": 0.0, "cost_center": test_cc},
			{"account": packaging_charges_account, "debit": 0.0, "credit": 250.0, "cost_center": test_cc},
		]
		self.assertEqual(expected_pr_gles, pr_gl_entries)

		# Make PI against Purchase Receipt
		pi = make_purchase_invoice(pr.name).save().submit()
		pi_gl_entries = get_gl_entries(pi.doctype, pi.name, skip_cancelled=True)
		expected_pi_gles = [
			{"account": stock_rbnb, "debit": 1000.0, "credit": 0.0, "cost_center": test_cc},
			{"account": packaging_charges_account, "debit": 250.0, "credit": 0.0, "cost_center": test_cc},
			{"account": creditors, "debit": 0.0, "credit": 1250.0, "cost_center": None},
		]
		self.assertEqual(expected_pi_gles, pi_gl_entries)

		lcv = self.create_lcv(pr.doctype, pr.name, test_company, lcv_expense_account)
		pr_gles_after_lcv = get_gl_entries(pr.doctype, pr.name, skip_cancelled=True)
		expected_pr_gles_after_lcv = [
			{"account": stock_rbnb, "debit": 0.0, "credit": 1000.0, "cost_center": test_cc},
			{"account": stock_in_hand, "debit": 1300.0, "credit": 0.0, "cost_center": test_cc},
			{"account": packaging_charges_account, "debit": 0.0, "credit": 250.0, "cost_center": test_cc},
			{"account": lcv_expense_account, "debit": 0.0, "credit": 50.0, "cost_center": test_cc},
		]
		self.assertEqual(expected_pr_gles_after_lcv, pr_gles_after_lcv)

		# Trigger Repost Item Valudation on a older date
		repost_doc = frappe.get_doc(
			{
				"doctype": "Repost Item Valuation",
				"based_on": "Item and Warehouse",
				"item_code": pr.items[0].item_code,
				"warehouse": pr.items[0].warehouse,
				"posting_date": add_days(pr.posting_date, -1),
				"posting_time": "00:00:00",
				"company": pr.company,
				"allow_negative_stock": 1,
				"via_landed_cost_voucher": 0,
				"allow_zero_rate": 0,
			}
		)
		repost_doc.save().submit()

		pr_gles_after_repost = get_gl_entries(pr.doctype, pr.name, skip_cancelled=True)
		expected_pr_gles_after_repost = [
			{"account": stock_rbnb, "debit": 0.0, "credit": 1000.0, "cost_center": test_cc},
			{"account": stock_in_hand, "debit": 1300.0, "credit": 0.0, "cost_center": test_cc},
			{"account": packaging_charges_account, "debit": 0.0, "credit": 250.0, "cost_center": test_cc},
			{"account": lcv_expense_account, "debit": 0.0, "credit": 50.0, "cost_center": test_cc},
		]
		self.assertEqual(len(pr_gles_after_repost), len(expected_pr_gles_after_repost))
		self.assertEqual(expected_pr_gles_after_repost, pr_gles_after_repost)

		# teardown
		lcv.reload()
		lcv.cancel()
		pi.reload()
		pi.cancel()
		pr.reload()
		pr.cancel()

		company_doc.enable_perpetual_inventory = False
		company_doc.stock_received_but_not_billed = None
		company_doc.default_inventory_account = None
		company_doc.save()

	def create_lcv(self, receipt_document_type, receipt_document, company, expense_account, charges=50):
		ref_doc = frappe.get_doc(receipt_document_type, receipt_document)

		lcv = frappe.new_doc("Landed Cost Voucher")
		lcv.company = company
		lcv.distribute_charges_based_on = "Qty"
		lcv.set(
			"purchase_receipts",
			[
				{
					"receipt_document_type": receipt_document_type,
					"receipt_document": receipt_document,
					"supplier": ref_doc.supplier,
					"posting_date": ref_doc.posting_date,
					"grand_total": ref_doc.base_grand_total,
				}
			],
		)

		lcv.set(
			"taxes",
			[
				{
					"description": "Testing",
					"expense_account": expense_account,
					"amount": charges,
				}
			],
		)
		lcv.save().submit()
		return lcv

	def test_tax_account_heads_on_item_repost_without_lcv(self):
		"""
		PO -> PR -> PI
		Backdated `Repost Item valuation` should not merge tax account heads into stock_rbnb if Purchase Receipt was created first
		This scenario is without LCV
		"""
		from erpnext.accounts.doctype.account.test_account import create_account
		from erpnext.buying.doctype.purchase_order.test_purchase_order import (
			create_purchase_order,
			make_pr_against_po,
		)
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice

		stock_rbnb = "Stock Received But Not Billed - _TC"
		stock_in_hand = "Stock In Hand - _TC"
		test_cc = "_Test Cost Center - _TC"
		test_company = "_Test Company"
		creditors = "Creditors - _TC"

		company_doc = frappe.get_doc("Company", test_company)
		company_doc.enable_perpetual_inventory = True
		company_doc.stock_received_but_not_billed = stock_rbnb
		company_doc.default_inventory_account = stock_in_hand
		company_doc.save()

		packaging_charges_account = create_account(
			account_name="Packaging Charges",
			parent_account="Indirect Expenses - _TC",
			company=test_company,
			account_type="Tax",
		)

		po = create_purchase_order(qty=10, rate=100, do_not_save=1)
		po.taxes = []
		po.append(
			"taxes",
			{
				"category": "Valuation and Total",
				"account_head": packaging_charges_account,
				"cost_center": test_cc,
				"description": "Test",
				"add_deduct_tax": "Add",
				"charge_type": "Actual",
				"tax_amount": 250,
			},
		)
		po.save().submit()

		pr = make_pr_against_po(po.name, received_qty=10)
		pr_gl_entries = get_gl_entries(pr.doctype, pr.name, skip_cancelled=True)
		expected_pr_gles = [
			{"account": stock_rbnb, "debit": 0.0, "credit": 1000.0, "cost_center": test_cc},
			{"account": stock_in_hand, "debit": 1250.0, "credit": 0.0, "cost_center": test_cc},
			{"account": packaging_charges_account, "debit": 0.0, "credit": 250.0, "cost_center": test_cc},
		]
		self.assertEqual(expected_pr_gles, pr_gl_entries)

		# Make PI against Purchase Receipt
		pi = make_purchase_invoice(pr.name).save().submit()
		pi_gl_entries = get_gl_entries(pi.doctype, pi.name, skip_cancelled=True)
		expected_pi_gles = [
			{"account": stock_rbnb, "debit": 1000.0, "credit": 0.0, "cost_center": test_cc},
			{"account": packaging_charges_account, "debit": 250.0, "credit": 0.0, "cost_center": test_cc},
			{"account": creditors, "debit": 0.0, "credit": 1250.0, "cost_center": None},
		]
		self.assertEqual(expected_pi_gles, pi_gl_entries)

		# Trigger Repost Item Valudation on a older date
		repost_doc = frappe.get_doc(
			{
				"doctype": "Repost Item Valuation",
				"based_on": "Item and Warehouse",
				"item_code": pr.items[0].item_code,
				"warehouse": pr.items[0].warehouse,
				"posting_date": add_days(pr.posting_date, -1),
				"posting_time": "00:00:00",
				"company": pr.company,
				"allow_negative_stock": 1,
				"via_landed_cost_voucher": 0,
				"allow_zero_rate": 0,
			}
		)
		repost_doc.save().submit()

		pr_gles_after_repost = get_gl_entries(pr.doctype, pr.name, skip_cancelled=True)
		expected_pr_gles_after_repost = [
			{"account": stock_rbnb, "debit": 0.0, "credit": 1000.0, "cost_center": test_cc},
			{"account": stock_in_hand, "debit": 1250.0, "credit": 0.0, "cost_center": test_cc},
			{"account": packaging_charges_account, "debit": 0.0, "credit": 250.0, "cost_center": test_cc},
		]
		self.assertEqual(len(pr_gles_after_repost), len(expected_pr_gles_after_repost))
		self.assertEqual(expected_pr_gles_after_repost, pr_gles_after_repost)

		# teardown
		pi.reload()
		pi.cancel()
		pr.reload()
		pr.cancel()

		company_doc.enable_perpetual_inventory = False
		company_doc.stock_received_but_not_billed = None
		company_doc.default_inventory_account = None
		company_doc.save()

	def test_do_not_use_batchwise_valuation_rate(self):
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

		item_code = "Test Item for Do Not Use Batchwise Valuation"
		make_item(
			item_code,
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "TIDNBV-.#####",
				"valuation_method": "Moving Average",
			},
		)

		# 1st pr for 100 rate
		pr = make_purchase_receipt(
			item_code=item_code,
			qty=1,
			rate=100,
			posting_date=add_days(today(), -2),
		)

		make_purchase_receipt(
			item_code=item_code,
			qty=1,
			rate=200,
			posting_date=add_days(today(), -1),
		)

		dn = create_delivery_note(
			item_code=item_code,
			qty=1,
			rate=300,
			posting_date=today(),
			use_serial_batch_fields=1,
			batch_no=get_batch_from_bundle(pr.items[0].serial_and_batch_bundle),
		)
		dn.reload()
		bundle = dn.items[0].serial_and_batch_bundle

		valuation_rate = frappe.db.get_value("Serial and Batch Bundle", bundle, "avg_rate")
		self.assertEqual(valuation_rate, 100.0)

		doc = frappe.get_doc("Stock Settings")
		doc.do_not_use_batchwise_valuation = 1
		doc.flags.ignore_validate = True
		doc.save()

		pr.repost_future_sle_and_gle(force=True)

		valuation_rate = frappe.db.get_value("Serial and Batch Bundle", bundle, "avg_rate")
		self.assertEqual(valuation_rate, 150)

		doc = frappe.get_doc("Stock Settings")
		doc.do_not_use_batchwise_valuation = 0
		doc.flags.ignore_validate = True
		doc.save()

	def test_status_mapping(self):
		item_code = "item_for_status"
		create_item(item_code)
		create_item("item_for_status")
		warehouse = create_warehouse("Stores")
		supplier = "Test Supplier"
		create_supplier(supplier_name=supplier)
		pr = make_purchase_receipt(
			item_code=item_code,
			warehouse=warehouse,
			qty=1,
			rate=0,
		)
		self.assertEqual(pr.grand_total, 0.0)
		self.assertEqual(pr.status, "Completed")

	def test_internal_transfer_for_batch_items_with_cancel(self):
		from erpnext.stock.doctype.delivery_note.delivery_note import make_inter_company_purchase_receipt
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

		frappe.db.set_single_value("Stock Settings", "use_serial_batch_fields", 0)

		prepare_data_for_internal_transfer()

		customer = "_Test Internal Customer 2"
		company = "_Test Company with perpetual inventory"

		batch_item_doc = make_item(
			"_Test Batch Item For Stock Transfer Cancel Case",
			{"has_batch_no": 1, "create_new_batch": 1, "batch_number_series": "USBF-BT-CANBIFST-.####"},
		)

		serial_item_doc = make_item(
			"_Test Serial No Item For Stock Transfer Cancel Case",
			{"has_serial_no": 1, "serial_no_series": "USBF-BT-CANBIFST-.####"},
		)

		inward_entry = make_purchase_receipt(
			item_code=batch_item_doc.name,
			qty=10,
			rate=150,
			warehouse="Stores - TCP1",
			company="_Test Company with perpetual inventory",
			use_serial_batch_fields=0,
			do_not_submit=1,
		)

		inward_entry.append(
			"items",
			{
				"item_code": serial_item_doc.name,
				"qty": 15,
				"rate": 250,
				"item_name": serial_item_doc.item_name,
				"conversion_factor": 1.0,
				"uom": serial_item_doc.stock_uom,
				"stock_uom": serial_item_doc.stock_uom,
				"warehouse": "Stores - TCP1",
				"use_serial_batch_fields": 0,
			},
		)

		inward_entry.submit()
		inward_entry.reload()

		for row in inward_entry.items:
			self.assertTrue(row.serial_and_batch_bundle)

		inter_transfer_dn = create_delivery_note(
			item_code=inward_entry.items[0].item_code,
			company=company,
			customer=customer,
			cost_center="Main - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			qty=10,
			rate=500,
			warehouse="Stores - TCP1",
			target_warehouse="Work In Progress - TCP1",
			batch_no=get_batch_from_bundle(inward_entry.items[0].serial_and_batch_bundle),
			use_serial_batch_fields=0,
			do_not_submit=1,
		)

		inter_transfer_dn.append(
			"items",
			{
				"item_code": serial_item_doc.name,
				"qty": 15,
				"rate": 350,
				"item_name": serial_item_doc.item_name,
				"conversion_factor": 1.0,
				"uom": serial_item_doc.stock_uom,
				"stock_uom": serial_item_doc.stock_uom,
				"warehouse": "Stores - TCP1",
				"target_warehouse": "Work In Progress - TCP1",
				"serial_no": "\n".join(
					get_serial_nos_from_bundle(inward_entry.items[1].serial_and_batch_bundle)
				),
				"use_serial_batch_fields": 0,
			},
		)

		inter_transfer_dn.submit()
		inter_transfer_dn.reload()
		for row in inter_transfer_dn.items:
			if row.item_code == batch_item_doc.name:
				self.assertEqual(row.rate, 150.0)
			else:
				self.assertEqual(row.rate, 250.0)

			self.assertTrue(row.serial_and_batch_bundle)

		inter_transfer_pr = make_inter_company_purchase_receipt(inter_transfer_dn.name)
		for row in inter_transfer_pr.items:
			row.from_warehouse = "Work In Progress - TCP1"
			row.warehouse = "Stores - TCP1"
		inter_transfer_pr.submit()

		for row in inter_transfer_pr.items:
			if row.item_code == batch_item_doc.name:
				self.assertEqual(row.rate, 150.0)
			else:
				self.assertEqual(row.rate, 250.0)

			self.assertTrue(row.serial_and_batch_bundle)

		inter_transfer_pr.cancel()
		inter_transfer_dn.cancel()

		frappe.db.set_single_value("Stock Settings", "use_serial_batch_fields", 1)

	def test_internal_transfer_for_batch_items_with_cancel_use_serial_batch_fields(self):
		from erpnext.stock.doctype.delivery_note.delivery_note import make_inter_company_purchase_receipt
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

		frappe.db.set_single_value("Stock Settings", "use_serial_batch_fields", 1)
		frappe.db.set_single_value("Stock Settings", "auto_create_serial_and_batch_bundle_for_outward", 0)

		prepare_data_for_internal_transfer()

		customer = "_Test Internal Customer 2"
		company = "_Test Company with perpetual inventory"

		batch_item_doc = make_item(
			"_Test Batch Item For Stock Transfer Cancel Case 11",
			{"has_batch_no": 1, "create_new_batch": 1, "batch_number_series": "USBF11-BT-CANBIFST-.####"},
		)

		serial_item_doc = make_item(
			"_Test Serial No Item For Stock Transfer Cancel Case 11",
			{"has_serial_no": 1, "serial_no_series": "USBF11-BT-CANBIFST-.####"},
		)

		inward_entry = make_purchase_receipt(
			item_code=batch_item_doc.name,
			qty=10,
			rate=150,
			warehouse="Stores - TCP1",
			company="_Test Company with perpetual inventory",
			use_serial_batch_fields=1,
			do_not_submit=1,
		)

		inward_entry.append(
			"items",
			{
				"item_code": serial_item_doc.name,
				"qty": 15,
				"rate": 250,
				"item_name": serial_item_doc.item_name,
				"conversion_factor": 1.0,
				"uom": serial_item_doc.stock_uom,
				"stock_uom": serial_item_doc.stock_uom,
				"warehouse": "Stores - TCP1",
				"use_serial_batch_fields": 1,
			},
		)

		inward_entry.submit()
		inward_entry.reload()

		for row in inward_entry.items:
			self.assertTrue(row.serial_and_batch_bundle)

		inter_transfer_dn = create_delivery_note(
			item_code=inward_entry.items[0].item_code,
			company=company,
			customer=customer,
			cost_center="Main - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			qty=10,
			rate=500,
			warehouse="Stores - TCP1",
			target_warehouse="Work In Progress - TCP1",
			batch_no=get_batch_from_bundle(inward_entry.items[0].serial_and_batch_bundle),
			use_serial_batch_fields=1,
			do_not_submit=1,
		)

		inter_transfer_dn.append(
			"items",
			{
				"item_code": serial_item_doc.name,
				"qty": 15,
				"rate": 350,
				"item_name": serial_item_doc.item_name,
				"conversion_factor": 1.0,
				"uom": serial_item_doc.stock_uom,
				"stock_uom": serial_item_doc.stock_uom,
				"warehouse": "Stores - TCP1",
				"target_warehouse": "Work In Progress - TCP1",
				"serial_no": "\n".join(
					get_serial_nos_from_bundle(inward_entry.items[1].serial_and_batch_bundle)
				),
				"use_serial_batch_fields": 1,
			},
		)

		inter_transfer_dn.submit()
		inter_transfer_dn.reload()
		for row in inter_transfer_dn.items:
			if row.item_code == batch_item_doc.name:
				self.assertEqual(row.rate, 150.0)
			else:
				self.assertEqual(row.rate, 250.0)

			self.assertTrue(row.serial_and_batch_bundle)

		inter_transfer_pr = make_inter_company_purchase_receipt(inter_transfer_dn.name)
		for row in inter_transfer_pr.items:
			row.from_warehouse = "Work In Progress - TCP1"
			row.warehouse = "Stores - TCP1"
		inter_transfer_pr.submit()

		for row in inter_transfer_pr.items:
			if row.item_code == batch_item_doc.name:
				self.assertEqual(row.rate, 150.0)
			else:
				self.assertEqual(row.rate, 250.0)

			self.assertTrue(row.serial_and_batch_bundle)

		inter_transfer_pr.cancel()
		inter_transfer_dn.cancel()
		frappe.db.set_single_value("Stock Settings", "auto_create_serial_and_batch_bundle_for_outward", 1)

	def test_sles_with_same_posting_datetime_and_creation(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
		from erpnext.stock.report.stock_balance.stock_balance import execute

		item_code = "Test Item for SLE with same posting datetime and creation"
		create_item(item_code)

		pr = make_purchase_receipt(
			item_code=item_code,
			qty=10,
			rate=100,
			posting_date="2023-11-06",
			posting_time="00:00:00",
		)

		sr = make_stock_entry(
			item_code=item_code,
			source=pr.items[0].warehouse,
			qty=10,
			posting_date="2023-11-07",
			posting_time="14:28:0.330404",
		)

		sle = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": sr.doctype, "voucher_no": sr.name, "item_code": sr.items[0].item_code},
			"name",
		)

		sle_doc = frappe.get_doc("Stock Ledger Entry", sle)
		sle_doc.db_set("creation", "2023-11-07 14:28:01.208930")

		sle_doc.reload()
		self.assertEqual(get_datetime(sle_doc.creation), get_datetime("2023-11-07 14:28:01.208930"))

		sr = make_stock_entry(
			item_code=item_code,
			target=pr.items[0].warehouse,
			qty=50,
			posting_date="2023-11-07",
			posting_time="14:28:0.920825",
		)

		sle = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": sr.doctype, "voucher_no": sr.name, "item_code": sr.items[0].item_code},
			"name",
		)

		sle_doc = frappe.get_doc("Stock Ledger Entry", sle)
		sle_doc.db_set("creation", "2023-11-07 14:28:01.044561")

		sle_doc.reload()
		self.assertEqual(get_datetime(sle_doc.creation), get_datetime("2023-11-07 14:28:01.044561"))

		pr.repost_future_sle_and_gle(force=True)

		columns, data = execute(
			filters=frappe._dict(
				{"item_code": item_code, "warehouse": pr.items[0].warehouse, "company": pr.company}
			)
		)

		self.assertEqual(data[0].get("bal_qty"), 50.0)

	def test_purchase_receipt_return_valuation_without_use_serial_batch_field(self):
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_return

		batch_item = make_item(
			"_Test Purchase Receipt Return Valuation Batch Item",
			properties={
				"has_batch_no": 1,
				"create_new_batch": 1,
				"is_stock_item": 1,
				"batch_number_series": "BRTN-TPRBI-.#####",
			},
		).name
		serial_item = make_item(
			"_Test Purchase Receipt Return Valuation Serial Item",
			properties={"has_serial_no": 1, "is_stock_item": 1, "serial_no_series": "SRTN-TPRSI-.#####"},
		).name
		rej_warehouse = create_warehouse("_Test Purchase Warehouse For Rejected Qty")
		pr = make_purchase_receipt(
			item_code=batch_item,
			received_qty=10,
			qty=8,
			rejected_qty=2,
			rejected_warehouse=rej_warehouse,
			rate=300,
			do_not_submit=1,
			use_serial_batch_fields=0,
		)
		pr.append(
			"items",
			{
				"item_code": serial_item,
				"qty": 2,
				"rate": 100,
				"base_rate": 100,
				"item_name": serial_item,
				"uom": "Nos",
				"stock_uom": "Nos",
				"conversion_factor": 1,
				"rejected_qty": 1,
				"warehouse": pr.items[0].warehouse,
				"use_serial_batch_fields": 0,
				"rejected_warehouse": rej_warehouse,
			},
		)
		pr.save()
		pr.submit()
		pr.reload()
		batch_no = get_batch_from_bundle(pr.items[0].serial_and_batch_bundle)
		rejected_batch_no = get_batch_from_bundle(pr.items[0].rejected_serial_and_batch_bundle)
		self.assertEqual(batch_no, rejected_batch_no)
		return_entry = make_purchase_return(pr.name)
		return_entry.save()
		return_entry.submit()
		return_entry.reload()
		for row in return_entry.items:
			if row.item_code == batch_item:
				bundle_data = frappe.get_all(
					"Serial and Batch Entry",
					filters={"parent": row.serial_and_batch_bundle},
					pluck="incoming_rate",
				)
				for incoming_rate in bundle_data:
					self.assertEqual(incoming_rate, 300.00)
			else:
				bundle_data = frappe.get_all(
					"Serial and Batch Entry",
					filters={"parent": row.serial_and_batch_bundle},
					pluck="incoming_rate",
				)
				for incoming_rate in bundle_data:
					self.assertEqual(incoming_rate, 100.00)
		for row in return_entry.items:
			if row.item_code == batch_item:
				bundle_data = frappe.get_all(
					"Serial and Batch Entry",
					filters={"parent": row.rejected_serial_and_batch_bundle},
					pluck="incoming_rate",
				)
				for incoming_rate in bundle_data:
					self.assertEqual(incoming_rate, 0)
			else:
				bundle_data = frappe.get_all(
					"Serial and Batch Entry",
					filters={"parent": row.rejected_serial_and_batch_bundle},
					pluck="incoming_rate",
				)
				for incoming_rate in bundle_data:
					self.assertEqual(incoming_rate, 0)

	def test_purchase_receipt_return_valuation_with_use_serial_batch_field(self):
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_return

		batch_item = make_item(
			"_Test Purchase Receipt Return Valuation With Batch Item",
			properties={"has_batch_no": 1, "create_new_batch": 1, "is_stock_item": 1},
		).name
		serial_item = make_item(
			"_Test Purchase Receipt Return Valuation With Serial Item",
			properties={"has_serial_no": 1, "is_stock_item": 1},
		).name
		rej_warehouse = create_warehouse("_Test Purchase Warehouse For Rejected Qty")
		batch_no = "BATCH-RTN-BNU-TPRBI-0001"
		serial_nos = ["SNU-RTN-TPRSI-0001", "SNU-RTN-TPRSI-0002", "SNU-RTN-TPRSI-0003"]
		if not frappe.db.exists("Batch", batch_no):
			frappe.get_doc(
				{
					"doctype": "Batch",
					"batch_id": batch_no,
					"item": batch_item,
				}
			).insert()
		for serial_no in serial_nos:
			if not frappe.db.exists("Serial No", serial_no):
				frappe.get_doc(
					{
						"doctype": "Serial No",
						"item_code": serial_item,
						"serial_no": serial_no,
					}
				).insert()
		pr = make_purchase_receipt(
			item_code=batch_item,
			received_qty=10,
			qty=8,
			rejected_qty=2,
			rejected_warehouse=rej_warehouse,
			batch_no=batch_no,
			use_serial_batch_fields=1,
			rate=300,
			do_not_submit=1,
		)
		pr.append(
			"items",
			{
				"item_code": serial_item,
				"qty": 2,
				"rate": 100,
				"base_rate": 100,
				"item_name": serial_item,
				"uom": "Nos",
				"stock_uom": "Nos",
				"conversion_factor": 1,
				"rejected_qty": 1,
				"warehouse": pr.items[0].warehouse,
				"use_serial_batch_fields": 1,
				"rejected_warehouse": rej_warehouse,
				"serial_no": "\n".join(serial_nos[:2]),
				"rejected_serial_no": serial_nos[2],
			},
		)
		pr.save()
		pr.submit()
		pr.reload()
		batch_no = get_batch_from_bundle(pr.items[0].serial_and_batch_bundle)
		rejected_batch_no = get_batch_from_bundle(pr.items[0].rejected_serial_and_batch_bundle)
		self.assertEqual(batch_no, rejected_batch_no)
		return_entry = make_purchase_return(pr.name)
		return_entry.save()
		return_entry.submit()
		return_entry.reload()
		for row in return_entry.items:
			if row.item_code == batch_item:
				bundle_data = frappe.get_all(
					"Serial and Batch Entry",
					filters={"parent": row.serial_and_batch_bundle},
					pluck="incoming_rate",
				)
				for incoming_rate in bundle_data:
					self.assertEqual(incoming_rate, 300.00)
			else:
				bundle_data = frappe.get_all(
					"Serial and Batch Entry",
					filters={"parent": row.serial_and_batch_bundle},
					pluck="incoming_rate",
				)
				for incoming_rate in bundle_data:
					self.assertEqual(incoming_rate, 100.00)
		for row in return_entry.items:
			if row.item_code == batch_item:
				bundle_data = frappe.get_all(
					"Serial and Batch Entry",
					filters={"parent": row.rejected_serial_and_batch_bundle},
					pluck="incoming_rate",
				)
				for incoming_rate in bundle_data:
					self.assertEqual(incoming_rate, 0)
			else:
				bundle_data = frappe.get_all(
					"Serial and Batch Entry",
					filters={"parent": row.rejected_serial_and_batch_bundle},
					pluck="incoming_rate",
				)
				for incoming_rate in bundle_data:
					self.assertEqual(incoming_rate, 0)

	def test_purchase_return_partial_debit_note(self):
		pr = make_purchase_receipt(
			company="_Test Company with perpetual inventory",
			warehouse="Stores - TCP1",
			supplier_warehouse="Work In Progress - TCP1",
		)
		return_pr = make_purchase_receipt(
			company="_Test Company with perpetual inventory",
			warehouse="Stores - TCP1",
			supplier_warehouse="Work In Progress - TCP1",
			is_return=1,
			return_against=pr.name,
			qty=-2,
			do_not_submit=1,
		)
		return_pr.items[0].purchase_receipt_item = pr.items[0].name
		return_pr.submit()
		# because new_doc isn't considering is_return portion of status_updater
		returned = frappe.get_doc("Purchase Receipt", return_pr.name)
		returned.update_prevdoc_status()
		pr.load_from_db()
		# Check if Original PR updated
		self.assertEqual(pr.items[0].returned_qty, 2)
		self.assertEqual(pr.per_returned, 40)
		# Create first partial debit_note
		pi_1 = make_purchase_invoice(return_pr.name)
		pi_1.items[0].qty = -1
		pi_1.submit()
		# Check if the first partial debit billing percentage got updated
		return_pr.reload()
		self.assertEqual(return_pr.per_billed, 50)
		self.assertEqual(return_pr.status, "Partly Billed")
		# Create second partial debit_note to complete the debit note
		pi_2 = make_purchase_invoice(return_pr.name)
		pi_2.items[0].qty = -1
		pi_2.submit()
		# Check if the second partial debit note billing percentage got updated
		return_pr.reload()
		self.assertEqual(return_pr.per_billed, 100)
		self.assertEqual(return_pr.status, "Completed")

	def test_do_not_allow_to_inward_same_serial_no_multiple_times(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		frappe.db.set_single_value("Stock Settings", "allow_existing_serial_no", 0)
		item_code = make_item(
			"Test Do Not Allow INWD Item 123", {"has_serial_no": 1, "serial_no_series": "SN-TDAISN-.#####"}
		).name
		pr = make_purchase_receipt(item_code=item_code, qty=1, rate=100, use_serial_batch_fields=1)
		serial_no = get_serial_nos_from_bundle(pr.items[0].serial_and_batch_bundle)[0]
		status = frappe.db.get_value("Serial No", serial_no, "status")
		self.assertTrue(status == "Active")
		make_stock_entry(
			item_code=item_code,
			source=pr.items[0].warehouse,
			qty=1,
			serial_no=serial_no,
			use_serial_batch_fields=1,
		)
		status = frappe.db.get_value("Serial No", serial_no, "status")
		self.assertFalse(status == "Active")
		pr = make_purchase_receipt(
			item_code=item_code, qty=1, rate=100, use_serial_batch_fields=1, do_not_submit=1
		)
		pr.items[0].serial_no = serial_no
		pr.save()
		self.assertRaises(frappe.exceptions.ValidationError, pr.submit)
		frappe.db.set_single_value("Stock Settings", "allow_existing_serial_no", 1)

	def test_seral_no_return_validation(self):
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import (
			make_purchase_return,
		)

		frappe.flags.through_repost_item_valuation = False

		sn_item_code = make_item(
			"Test Serial No for Validation", {"has_serial_no": 1, "serial_no_series": "SN-TSNFVAL-.#####"}
		).name
		pr1 = make_purchase_receipt(item_code=sn_item_code, qty=5, rate=100, use_serial_batch_fields=1)
		pr1_serial_nos = get_serial_nos_from_bundle(pr1.items[0].serial_and_batch_bundle)
		serial_no_pr = make_purchase_receipt(
			item_code=sn_item_code, qty=5, rate=100, use_serial_batch_fields=1
		)
		serial_no_pr_serial_nos = get_serial_nos_from_bundle(serial_no_pr.items[0].serial_and_batch_bundle)
		sn_return = make_purchase_return(serial_no_pr.name)
		sn_return.items[0].qty = -1
		sn_return.items[0].received_qty = -1
		sn_return.items[0].serial_no = pr1_serial_nos[0]
		sn_return.save()
		self.assertRaises(frappe.ValidationError, sn_return.submit)
		sn_return = make_purchase_return(serial_no_pr.name)
		sn_return.items[0].qty = -1
		sn_return.items[0].received_qty = -1
		sn_return.items[0].serial_no = serial_no_pr_serial_nos[0]
		sn_return.save()
		sn_return.submit()

	def test_batch_no_return_validation(self):
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import (
			make_purchase_return,
		)

		frappe.flags.through_repost_item_valuation = False

		batch_item_code = make_item(
			"Test Batch No for Validation",
			{"has_batch_no": 1, "batch_number_series": "BT-TSNFVAL-.#####", "create_new_batch": 1},
		).name
		pr1 = make_purchase_receipt(item_code=batch_item_code, qty=5, rate=100, use_serial_batch_fields=1)
		batch_no = get_batch_from_bundle(pr1.items[0].serial_and_batch_bundle)
		batch_no_pr = make_purchase_receipt(
			item_code=batch_item_code, qty=5, rate=100, use_serial_batch_fields=1
		)
		original_batch_no = get_batch_from_bundle(batch_no_pr.items[0].serial_and_batch_bundle)
		batch_return = make_purchase_return(batch_no_pr.name)
		batch_return.items[0].qty = -1
		batch_return.items[0].received_qty = -1
		batch_return.items[0].batch_no = batch_no
		batch_return.save()
		self.assertRaises(frappe.ValidationError, batch_return.submit)
		batch_return = make_purchase_return(batch_no_pr.name)
		batch_return.items[0].qty = -1
		batch_return.items[0].received_qty = -1
		batch_return.items[0].batch_no = original_batch_no
		batch_return.save()
		batch_return.submit()

	def test_pr_status_based_on_invoices_with_update_stock(self):
		from erpnext.buying.doctype.purchase_order.purchase_order import (
			make_purchase_invoice as _make_purchase_invoice,
		)
		from erpnext.buying.doctype.purchase_order.purchase_order import (
			make_purchase_receipt as _make_purchase_receipt,
		)
		from erpnext.buying.doctype.purchase_order.test_purchase_order import (
			create_purchase_order,
		)

		item_code = "Test Item for PR Status Based on Invoices"
		create_item(item_code)

		po = create_purchase_order(item_code=item_code, qty=10)
		pi = _make_purchase_invoice(po.name)
		pi.update_stock = 1
		pi.items[0].qty = 5
		pi.submit()

		po.reload()
		self.assertEqual(po.per_billed, 50)

		pr = _make_purchase_receipt(po.name)
		self.assertEqual(pr.items[0].qty, 5)
		pr.submit()
		pr.reload()
		self.assertEqual(pr.status, "To Bill")

	def test_recreate_stock_ledgers(self):
		item_code = "Test Item for Recreate Stock Ledgers"
		create_item(item_code)

		pr = make_purchase_receipt(item_code=item_code, qty=10, rate=100)
		pr.submit()

		sles = frappe.get_all(
			"Stock Ledger Entry",
			filters={"voucher_type": pr.doctype, "voucher_no": pr.name},
			pluck="name",
		)

		self.assertTrue(sles)

		for row in sles:
			doc = frappe.get_doc("Stock Ledger Entry", row)
			doc.delete()

		sles = frappe.get_all(
			"Stock Ledger Entry",
			filters={"voucher_type": pr.doctype, "voucher_no": pr.name},
			pluck="name",
		)

		self.assertFalse(sles)

		frappe.get_doc(
			{
				"doctype": "Repost Item Valuation",
				"based_on": "Transaction",
				"voucher_type": pr.doctype,
				"voucher_no": pr.name,
				"posting_date": pr.posting_date,
				"posting_time": pr.posting_time,
				"company": pr.company,
				"recreate_stock_ledgers": 1,
			}
		).submit()

		sles = frappe.get_all(
			"Stock Ledger Entry",
			filters={"voucher_type": pr.doctype, "voucher_no": pr.name},
			pluck="name",
		)

		self.assertTrue(sles)

	def test_internal_pr_qty_change_only_single_batch(self):
		from erpnext.stock.doctype.delivery_note.delivery_note import make_inter_company_purchase_receipt
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

		prepare_data_for_internal_transfer()

		def get_sabb_qty(sabb):
			return frappe.get_value("Serial and Batch Bundle", sabb, "total_qty")

		item = make_item("Item with only Batch", {"has_batch_no": 1})
		item.create_new_batch = 1
		item.save()

		make_purchase_receipt(
			item_code=item.item_code,
			qty=10,
			rate=100,
			company="_Test Company with perpetual inventory",
			warehouse="Stores - TCP1",
		)

		dn = create_delivery_note(
			item_code=item.item_code,
			qty=10,
			rate=100,
			company="_Test Company with perpetual inventory",
			customer="_Test Internal Customer 2",
			cost_center="Main - TCP1",
			warehouse="Stores - TCP1",
			target_warehouse="Work In Progress - TCP1",
		)
		pr = make_inter_company_purchase_receipt(dn.name)

		pr.items[0].warehouse = "Stores - TCP1"
		pr.items[0].qty = 8
		pr.save()

		# Test 1 - Check if SABB qty is changed on first save
		self.assertEqual(abs(get_sabb_qty(pr.items[0].serial_and_batch_bundle)), 8)

		pr.items[0].qty = 6
		pr.items[0].received_qty = 6
		pr.save()

		# Test 2 - Check if SABB qty is changed when saved again
		self.assertEqual(abs(get_sabb_qty(pr.items[0].serial_and_batch_bundle)), 6)

		pr.items[0].qty = 12
		pr.items[0].received_qty = 12

		# Test 3 - OverAllowanceError should be thrown as qty is greater than qty in DN
		self.assertRaises(erpnext.controllers.status_updater.OverAllowanceError, pr.submit)

	def test_valuation_rate_for_rejected_materials(self):
		item = make_item("Test Item with Rej Material Valuation", {"is_stock_item": 1})
		company = "_Test Company with perpetual inventory"

		warehouse = create_warehouse(
			"_Test In-ward Warehouse",
			company="_Test Company with perpetual inventory",
		)

		rej_warehouse = create_warehouse(
			"_Test Warehouse - Rejected Material",
			company="_Test Company with perpetual inventory",
		)

		frappe.db.set_single_value("Buying Settings", "bill_for_rejected_quantity_in_purchase_invoice", 1)

		frappe.db.set_single_value("Buying Settings", "set_valuation_rate_for_rejected_materials", 1)

		pr = make_purchase_receipt(
			item_code=item.name,
			qty=10,
			rate=100,
			company=company,
			warehouse=warehouse,
			rejected_qty=5,
			rejected_warehouse=rej_warehouse,
		)

		stock_received_but_not_billed_account = frappe.get_value(
			"Company",
			company,
			"stock_received_but_not_billed",
		)

		rejected_item_cost = frappe.db.get_value(
			"Stock Ledger Entry",
			{
				"voucher_type": "Purchase Receipt",
				"voucher_no": pr.name,
				"warehouse": rej_warehouse,
			},
			"stock_value_difference",
		)

		self.assertEqual(rejected_item_cost, 500)

		srbnb_cost = frappe.db.get_value(
			"GL Entry",
			{
				"voucher_type": "Purchase Receipt",
				"voucher_no": pr.name,
				"account": stock_received_but_not_billed_account,
			},
			"credit",
		)

		self.assertEqual(srbnb_cost, 1500)

		frappe.db.set_single_value("Buying Settings", "bill_for_rejected_quantity_in_purchase_invoice", 0)

		frappe.db.set_single_value("Buying Settings", "set_valuation_rate_for_rejected_materials", 0)

	def test_no_valuation_rate_for_rejected_materials(self):
		item = make_item("Test Item with Rej Material No Valuation", {"is_stock_item": 1})
		company = "_Test Company with perpetual inventory"

		warehouse = create_warehouse(
			"_Test In-ward Warehouse",
			company="_Test Company with perpetual inventory",
		)

		rej_warehouse = create_warehouse(
			"_Test Warehouse - Rejected Material",
			company="_Test Company with perpetual inventory",
		)

		frappe.db.set_single_value("Buying Settings", "bill_for_rejected_quantity_in_purchase_invoice", 0)

		frappe.db.set_single_value("Buying Settings", "set_valuation_rate_for_rejected_materials", 0)

		pr = make_purchase_receipt(
			item_code=item.name,
			qty=10,
			rate=100,
			company=company,
			warehouse=warehouse,
			rejected_qty=5,
			rejected_warehouse=rej_warehouse,
		)

		stock_received_but_not_billed_account = frappe.get_value(
			"Company",
			company,
			"stock_received_but_not_billed",
		)

		rejected_item_cost = frappe.db.get_value(
			"Stock Ledger Entry",
			{
				"voucher_type": "Purchase Receipt",
				"voucher_no": pr.name,
				"warehouse": rej_warehouse,
			},
			"stock_value_difference",
		)

		self.assertEqual(rejected_item_cost, 0.0)

		srbnb_cost = frappe.db.get_value(
			"GL Entry",
			{
				"voucher_type": "Purchase Receipt",
				"voucher_no": pr.name,
				"account": stock_received_but_not_billed_account,
			},
			"credit",
		)

		self.assertEqual(srbnb_cost, 1000)

	def test_purchase_order_and_receipt_TC_SCK_072(self):
		company = "_Test Company"
		company_doc = frappe.get_doc("Company", company)
		if not company_doc.stock_received_but_not_billed:
			company_doc.stock_received_but_not_billed = "Stock Received But Not Billed - _TC"
			company_doc.save()

		item1 = make_item("ST-N-001", {"is_stock_item": 1, "gst_hsn_code": "01011010"})
		item2 = make_item("W-N-001", {"is_stock_item": 1, "gst_hsn_code": "01011020"})
		warehouse1 = create_warehouse("Raw Material - Iron Building - _TC", company=company)
		warehouse2 = create_warehouse("Woods - _TC", company=company)
		posting_date = "2024-12-31"

		# Create Purchase Order
		po = frappe.new_doc("Purchase Order")
		po.company = company
		po.supplier = "_Test Supplier"
		po.transaction_date = posting_date
		po.schedule_date = "2025-01-02"
		item_list = [
			{"item_code": item1.name, "rate": 50, "qty": 150, "warehouse": warehouse1},
			{"item_code": item2.name, "rate": 55, "qty": 75, "warehouse": warehouse2},
		]
		for row in item_list:
			po.append("items", row)
		po.insert()
		po.submit()

		self.assertEqual(po.items[0].item_code, item1.name)
		self.assertEqual(po.items[0].qty, 150)
		self.assertEqual(po.items[0].warehouse, warehouse1)
		self.assertEqual(po.items[1].item_code, item2.name)
		self.assertEqual(po.items[1].qty, 75)
		self.assertEqual(po.items[1].warehouse, warehouse2)

		# Check PO status
		self.assertEqual(po.status, "To Receive and Bill")

		# Create Purchase Receipt
		pr = make_purchase_receipt_with_multiple_items(
			purchase_order=po.name,
			company=company,
			supplier=po.supplier,
			currency=po.currency,
			posting_date=posting_date,
			items=item_list,
		)
		self.assertEqual(pr.items[0].item_code, item1.name)
		self.assertEqual(pr.items[0].qty, 150)
		self.assertEqual(pr.items[0].warehouse, warehouse1)
		self.assertEqual(pr.items[1].item_code, item2.name)
		self.assertEqual(pr.items[1].qty, 75)
		self.assertEqual(pr.items[1].warehouse, warehouse2)

		# Check PR status
		self.assertEqual(pr.status, "To Bill")

		# Check Stock Ledger Entries
		sl_entries = get_sl_entries("Purchase Receipt", pr.name)
		self.assertEqual(len(sl_entries), 2)
		self.assertEqual(sl_entries[0].warehouse, warehouse1)
		self.assertEqual(sl_entries[1].warehouse, warehouse2)

	def test_purchase_order_and_receipt_TC_SCK_073(self):
		from datetime import datetime, timedelta

		from erpnext.stock.utils import get_or_create_fiscal_year

		create_supplier(supplier_name="_Test Supplier", default_currency="INR")
		company = "_Test Indian Registered Company"
		frappe.db.set_value("GST Settings", "GST Settings", "enable_overseas_transactions", 1)
		create_company(company)
		get_or_create_fiscal_year(company)
		item1 = make_item("ST-N-001", {"is_stock_item": 1, "gst_hsn_code": "01011010"})
		item2 = make_item("W-N-001", {"is_stock_item": 1, "gst_hsn_code": "01011020"})
		warehouse1 = create_warehouse("Raw Material Iron Building - _TIRC", company=company)
		warehouse2 = create_warehouse("Woods - _TIRC", company=company)
		rejected_warehouse = create_warehouse("Rejection Scrap - _TIRC", company=company)
		posting_date = datetime.today().date()

		# Create Purchase Order
		po = frappe.new_doc("Purchase Order")
		po.company = company
		po.supplier = "_Test Supplier"
		po.transaction_date = posting_date
		po.schedule_date = datetime.today().date() + timedelta(days=15)
		item_list = [
			{"item_code": item1.name, "rate": 50, "qty": 150, "warehouse": warehouse1},
			{"item_code": item2.name, "rate": 55, "qty": 75, "warehouse": warehouse2},
		]
		for row in item_list:
			po.append("items", row)
		po.insert()
		po.submit()

		self.assertEqual(po.items[0].item_code, item1.name)
		self.assertEqual(po.items[0].qty, 150)
		self.assertEqual(po.items[0].warehouse, warehouse1)
		self.assertEqual(po.items[1].item_code, item2.name)
		self.assertEqual(po.items[1].qty, 75)
		self.assertEqual(po.items[1].warehouse, warehouse2)

		# Check PO status
		self.assertEqual(po.status, "To Receive and Bill")

		item_list[0]["qty"] = 100
		item_list[0]["rejected_qty"] = 50
		item_list[0]["rejected_warehouse"] = rejected_warehouse
		item_list[1]["qty"] = 50
		item_list[1]["rejected_qty"] = 25
		item_list[1]["rejected_warehouse"] = rejected_warehouse

		# Create Purchase Receipt
		pr = make_purchase_receipt_with_multiple_items(
			purchase_order=po.name,
			company=company,
			supplier=po.supplier,
			posting_date=posting_date,
			items=item_list,
			currency="USD",
		)
		pr.save()
		pr.submit()

		self.assertEqual(pr.items[0].item_code, item1.name)
		self.assertEqual(pr.items[0].qty, 100)
		self.assertEqual(pr.items[0].warehouse, warehouse1)
		self.assertEqual(pr.items[0].rejected_qty, 50)
		self.assertEqual(pr.items[0].rejected_warehouse, rejected_warehouse)
		self.assertEqual(pr.items[1].item_code, item2.name)
		self.assertEqual(pr.items[1].qty, 50)
		self.assertEqual(pr.items[1].warehouse, warehouse2)
		self.assertEqual(pr.items[1].rejected_qty, 25)
		self.assertEqual(pr.items[1].rejected_warehouse, rejected_warehouse)

		# Check PR status
		self.assertEqual(pr.status, "To Bill")

		# Check Stock Ledger Entries
		sl_entries = get_sl_entries("Purchase Receipt", pr.name)
		self.assertEqual(len(sl_entries), 4)
		self.assertEqual(sl_entries[0].warehouse, warehouse1)
		self.assertEqual(sl_entries[1].warehouse, rejected_warehouse)
		self.assertEqual(sl_entries[2].warehouse, warehouse2)
		self.assertEqual(sl_entries[3].warehouse, rejected_warehouse)

	def test_purchase_order_and_receipt_TC_SCK_074(self):
		from datetime import datetime, timedelta

		from erpnext.stock.utils import get_or_create_fiscal_year

		create_supplier(supplier_name="_Test Supplier", default_currency="INR")
		company = "_Test Indian Registered Company"
		create_company(company)
		get_or_create_fiscal_year(company)
		frappe.db.set_value("GST Settings", "GST Settings", "enable_overseas_transactions", 1)
		item1 = make_item("ST-N-001", {"is_stock_item": 1, "gst_hsn_code": "01011010"})
		item2 = make_item("W-N-001", {"is_stock_item": 1, "gst_hsn_code": "01011020"})
		warehouse1 = create_warehouse("Raw Material Iron Building - _TIRC", company=company)
		warehouse2 = create_warehouse("Woods - _TIRC", company=company)
		rejected_warehouse = create_warehouse("Rejection Scrap - _TIRC", company=company)
		posting_date = datetime.today().date()

		# Create Purchase Order
		po = frappe.new_doc("Purchase Order")
		po.company = company
		po.supplier = "_Test Supplier"
		po.transaction_date = posting_date
		po.schedule_date = datetime.today().date() + timedelta(days=15)
		item_list = [
			{"item_code": item1.name, "rate": 50, "qty": 150, "warehouse": warehouse1},
			{"item_code": item2.name, "rate": 55, "qty": 75, "warehouse": warehouse2},
		]
		for row in item_list:
			po.append("items", row)
		po.insert()
		po.submit()

		self.assertEqual(po.items[0].item_code, item1.name)
		self.assertEqual(po.items[0].qty, 150)
		self.assertEqual(po.items[0].warehouse, warehouse1)
		self.assertEqual(po.items[1].item_code, item2.name)
		self.assertEqual(po.items[1].qty, 75)
		self.assertEqual(po.items[1].warehouse, warehouse2)

		# Check PO status
		self.assertEqual(po.status, "To Receive and Bill")
		item_list[0]["qty"] = 0
		item_list[0]["rejected_qty"] = 150
		item_list[0]["rejected_warehouse"] = rejected_warehouse
		item_list[1]["qty"] = 0
		item_list[1]["rejected_qty"] = 75
		item_list[1]["rejected_warehouse"] = rejected_warehouse

		# Create Purchase Receipt
		pr = make_purchase_receipt_with_multiple_items(
			purchase_order=po.name,
			company=company,
			supplier=po.supplier,
			posting_date=posting_date,
			items=item_list,
			currency="USD",
		)
		pr.save()
		pr.submit()

		self.assertEqual(pr.items[0].item_code, item1.name)
		self.assertEqual(pr.items[0].qty, 0)
		self.assertEqual(pr.items[0].rejected_qty, 150)
		self.assertEqual(pr.items[0].rejected_warehouse, rejected_warehouse)
		self.assertEqual(pr.items[1].item_code, item2.name)
		self.assertEqual(pr.items[1].qty, 0)
		self.assertEqual(pr.items[1].rejected_qty, 75)
		self.assertEqual(pr.items[1].rejected_warehouse, rejected_warehouse)

		# Check PR status
		self.assertEqual(pr.status, "Completed")

		# Check Stock Ledger Entries
		sl_entries = get_sl_entries("Purchase Receipt", pr.name)
		self.assertEqual(len(sl_entries), 2)
		self.assertEqual(sl_entries[0].warehouse, rejected_warehouse)
		self.assertEqual(sl_entries[1].warehouse, rejected_warehouse)

	def test_direct_create_purchase_receipt(self):
		item = create_item("OP-MB-001")
		pr = make_purchase_receipt(qty=10, item_code=item, rate=10000)

		self.assertEqual(pr.status, "To Bill")
		se = frappe.get_doc("Stock Ledger Entry", {"voucher_type": "Purchase Receipt", "voucher_no": pr.name})
		self.assertEqual(se.get("qty_after_transaction"), 10)
		self.assertEqual(se.get("valuation_rate"), 10000)
		self.assertEqual(se.get("warehouse"), pr.get("items")[0].warehouse)

	def test_direct_create_purchase_return_partial_TC_SCK_039(self):
		company = "_Test Company"
		company_doc = frappe.get_doc("Company", company)
		if not company_doc.stock_received_but_not_billed:
			company_doc.stock_received_but_not_billed = "Stock Received But Not Billed - _TC"
			company_doc.save()
		pr = make_purchase_receipt(qty=10, rate=10000)
		from erpnext.controllers.sales_and_purchase_return import make_return_doc

		return_pr = make_return_doc("Purchase Receipt", pr.name)
		bin_qty = frappe.db.get_value(
			"Bin",
			{"item_code": return_pr.items[0].item_code, "warehouse": return_pr.items[0].warehouse},
			"actual_qty",
		)
		return_pr.items[0].qty = -5
		return_pr.items[0].received_qty = -5
		return_pr.submit()

		self.assertEqual(pr.status, "To Bill")
		se = frappe.get_doc("Stock Ledger Entry", {"voucher_type": "Purchase Receipt", "voucher_no": pr.name})
		self.assertEqual(se.get("qty_after_transaction"), bin_qty)
		self.assertEqual(se.get("warehouse"), pr.get("items")[0].warehouse)

	def test_direct_create_purchase_receipt_return_TC_SCK_030(self):
		company = "_Test Company"
		company_doc = frappe.get_doc("Company", company)
		if not company_doc.stock_received_but_not_billed:
			company_doc.stock_received_but_not_billed = "Stock Received But Not Billed - _TC"
			company_doc.save()
		pr = make_purchase_receipt(
			qty=10,
			rate=10,
		)

		return_pr = make_purchase_receipt(
			is_return=1,
			return_against=pr.name,
			qty=-10,
			rate=10,
			do_not_submit=1,
		)
		return_pr.items[0].purchase_receipt_item = pr.items[0].name
		return_pr.submit()

		# hack because new_doc isn't considering is_return portion of status_updater
		returned = frappe.get_doc("Purchase Receipt", return_pr.name)
		returned.update_prevdoc_status()
		pr.load_from_db()

		self.assertEqual(pr.status, "Return Issued")
		se = frappe.get_doc(
			"Stock Ledger Entry", {"voucher_type": "Purchase Receipt", "voucher_no": return_pr.name}
		)
		self.assertEqual(se.get("actual_qty"), -10)
		return_pr.cancel()
		pr.cancel()

	def test_direct_create_purchase_receipt_and_cancel_TC_SCK_53(self):
		from erpnext.stock.doctype.material_request.test_material_request import get_gle

		fields = {"has_batch_no": 1, "batch_number_series": "BT-BATCHITEM-.#####", "create_new_batch": 1}
		if frappe.db.has_column("Item", "gst_hsn_code"):
			fields["gst_hsn_code"] = "01011010"

		batch_item_code = make_item("Test Batch Item", fields).name
		frappe.db.set_value("Company", "_Test Company", "enable_perpetual_inventory", 1)
		frappe.db.set_value(
			"Company", "_Test Company", "stock_received_but_not_billed", "Stock Received But Not Billed - _TC"
		)
		pr = make_purchase_receipt(item_code=batch_item_code, qty=10, rate=100, use_serial_batch_fields=1)

		self.assertEqual(pr.status, "To Bill")

		# check sle
		sl_entries = get_sl_entries("Purchase Receipt", pr.name)

		expected_sle = {"_Test Warehouse - _TC": 10}

		# Validate sle
		for sle in sl_entries:
			self.assertEqual(expected_sle[sle.warehouse], sle.actual_qty)

		# check gl entries
		gl_entries = get_gl_entries("Purchase Receipt", pr.name)

		self.assertTrue(gl_entries)
		stock_in_hand_account = get_inventory_account(pr.company, "_Test Warehouse - _TC")

		expected_values = {
			stock_in_hand_account: [1000.0, 0.0],
			"Stock Received But Not Billed - _TC": [0.0, 1000.0],
		}

		for gle in gl_entries:
			self.assertEqual(expected_values[gle.account][0], gle.debit)
			self.assertEqual(expected_values[gle.account][1], gle.credit)

		pr.cancel()

		# SL and GL entries after cancel
		sl_entries = get_sl_entries("Purchase Receipt", pr.name)
		sh_gle = get_gle(pr.company, pr.name, stock_in_hand_account)
		srbnb_gle = get_gle(pr.company, pr.name, "Stock Received But Not Billed - _TC")
		self.assertEqual(pr.status, "Cancelled")
		self.assertEqual(sl_entries[0]["actual_qty"], -10)
		self.assertEqual(sh_gle[0], sh_gle[1])
		self.assertEqual(srbnb_gle[0], srbnb_gle[1])

	def test_create_2pr_with_item_fifo_and_sr_TC_SCK_14(self):
		self._test_create_2pr_with_item_fifo_and_sr()

	def test_create_2pr_with_item_fifo_and_sr_and_cancel_TC_SCK_59(self):
		sr = self._test_create_2pr_with_item_fifo_and_sr()

		# Cancel Stock Reco and check SLE and GL
		sr.cancel()
		self.check_cancel_stock_gl_sle(sr, 20, -3000.0)

	def test_purchase_receipt_with_serialized_item_TC_SCK_145(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
		from erpnext.stock.utils import get_or_create_fiscal_year

		create_company()
		supplier = create_supplier(supplier_name="Test Supplier 1")
		get_or_create_fiscal_year("_Test Company")
		parent_itm_grp = frappe.new_doc("Item Group")
		parent_itm_grp.item_group_name = "Test Parent Item Group"
		parent_itm_grp.is_group = 1
		parent_itm_grp.insert()
		itm_grp = frappe.new_doc("Item Group")
		itm_grp.item_group_name = "Test Item Group"
		itm_grp.parent_item_group = "Test Parent Item Group"
		itm_grp.insert()
		item_code = "ADI-SH-W09"
		warehouse = "Stores - _TC"
		supplier = "Test Supplier 1"
		company = "_Test Company"
		qty = 5

		if not frappe.db.exists("Item", item_code):
			item = frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": item_code,
					"item_name": item_code,
					"item_group": "Test Item Group",
					"is_stock_item": 1,
					"is_purchase_item": 1,
					"gst_hsn_code": "01011010",
					"has_serial_no": 1,
					"serial_no_series": "SERI-.#####",
					"company": company,
				}
			)
			item.insert()

		pr = frappe.get_doc(
			{
				"doctype": "Purchase Receipt",
				"supplier": supplier,
				"company": company,
				"posting_date": "2025-01-03",
				"set_warehouse": warehouse,
				"items": [{"item_code": item_code, "warehouse": warehouse, "qty": qty, "rate": 100}],
			}
		)
		pr.insert()
		pr.submit()

		self.assertEqual(pr.docstatus, 1)
		self.assertEqual(len(pr.items), 1)
		self.assertEqual(pr.items[0].item_code, item_code)
		self.assertEqual(pr.items[0].qty, qty)

		serial_batch_bundle = frappe.db.get_value("Serial and Batch Bundle", {"voucher_no": pr.name}, "name")
		serial_nos = frappe.db.get_all(
			"Serial and Batch Entry", {"parent": serial_batch_bundle}, ["serial_no"]
		)
		self.assertEqual(len(serial_nos), qty)

		for serial_no in serial_nos:
			status = frappe.db.get_value("Serial No", serial_no, "status")
			self.assertEqual(status, "Active")

	def _test_create_2pr_with_item_fifo_and_sr(self):
		from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
			create_stock_reconciliation,
		)

		fields = {"is_stock_item": 1, "valuation_method": "FIFO"}
		frappe.db.set_value("Company", "_Test Company", "enable_perpetual_inventory", 1)
		frappe.db.set_value(
			"Company", "_Test Company", "stock_received_but_not_billed", "Stock Received But Not Billed - _TC"
		)
		if frappe.db.has_column("Item", "gst_hsn_code"):
			fields["gst_hsn_code"] = "01011010"

		item = make_item("_Test Item For FIFO", properties=fields).name
		warehouse = "_Test Warehouse - _TC"
		pr = make_purchase_receipt(item_code=item, qty=10, rate=500)

		# Validate sle for PR 1
		expected_sle = {"_Test Warehouse - _TC": [10, 10, 5000, 500, "[[10.0, 500.0]]"]}
		self.val_method_sl_entry(pr, expected_sle)

		pr1 = make_purchase_receipt(item_code=item, qty=10, rate=600)

		# Validate sle for PR 2
		expected_sle = {"_Test Warehouse - _TC": [10, 20, 6000, 550, "[[10.0, 500.0], [10.0, 600.0]]"]}
		self.val_method_sl_entry(pr1, expected_sle)

		# Create Stock Reco
		sr = create_stock_reconciliation(
			item_code=item,
			qty=20,
			rate=700,
			warehouse=warehouse,
			expense_account="Stock Adjustment - _TC",
		)

		stock_in_hand_account = get_inventory_account(pr.company, "_Test Warehouse - _TC")
		expected_sle = {"_Test Warehouse - _TC": [0, 20, 3000, 700, "[[20.0, 700.0]]"]}
		expected_gl = {
			stock_in_hand_account: [3000.0, 0.0],
			"Stock Adjustment - _TC": [0.0, 3000.0],
		}

		# Validate sle and gl stock reco
		self.val_method_sl_entry(sr, expected_sle)
		self.check_gl_entry(sr, expected_gl)

		return sr

	def test_create_2pr_with_item_mov_avg_and_sr_TC_SCK_15(self):
		self._test_create_2pr_with_item_mov_avg_and_sr()

	def test_create_2pr_with_item_mov_avg_and_sr_and_cancel_TC_SCK_60(self):
		sr = self._test_create_2pr_with_item_mov_avg_and_sr()

		# Cancel Stock Reco and check SLE and GL
		sr.cancel()
		self.check_cancel_stock_gl_sle(sr, 20, -30000.0)

	def _test_create_2pr_with_item_mov_avg_and_sr(self):
		from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
			create_stock_reconciliation,
		)

		fields = {"is_stock_item": 1, "valuation_method": "Moving Average"}
		frappe.db.set_value("Company", "_Test Company", "enable_perpetual_inventory", 1)
		frappe.db.set_value(
			"Company", "_Test Company", "stock_received_but_not_billed", "Stock Received But Not Billed - _TC"
		)
		if frappe.db.has_column("Item", "gst_hsn_code"):
			fields["gst_hsn_code"] = "01011010"

		item = make_item("_Test Item For Moving Average", properties=fields).name
		warehouse = "_Test Warehouse - _TC"
		pr = make_purchase_receipt(item_code=item, qty=10, rate=5000)

		expected_sle = {"_Test Warehouse - _TC": [10, 10, 50000, 5000, "[]"]}

		# Validate sle for PR 1
		self.val_method_sl_entry(pr, expected_sle)

		pr1 = make_purchase_receipt(item_code=item, qty=10, rate=6000)

		expected_sle = {"_Test Warehouse - _TC": [10, 20, 60000, 5500, "[]"]}

		# Validate sle for PR 2
		self.val_method_sl_entry(pr1, expected_sle)

		# Create Stock Reco
		sr = create_stock_reconciliation(
			item_code=item,
			qty=20,
			rate=7000,
			warehouse=warehouse,
			expense_account="Stock Adjustment - _TC",
		)

		stock_in_hand_account = get_inventory_account(pr.company, "_Test Warehouse - _TC")
		expected_sle = {"_Test Warehouse - _TC": [0, 20, 30000, 7000, "[]"]}
		expected_gl = {
			stock_in_hand_account: [30000.0, 0.0],
			"Stock Adjustment - _TC": [0.0, 30000.0],
		}

		# Validate sle and gl stock reco
		self.val_method_sl_entry(sr, expected_sle)
		self.check_gl_entry(sr, expected_gl)

		return sr

	def check_cancel_stock_gl_sle(self, doc, exp_qty, exp_amt):
		from erpnext.stock.doctype.material_request.test_material_request import get_gle

		sl_entry_cancelled = frappe.db.get_all(
			"Stock Ledger Entry",
			{"voucher_type": doc.doctype, "voucher_no": doc.name},
			["qty_after_transaction", "stock_value_difference"],
			order_by="creation",
		)
		self.assertEqual(len(sl_entry_cancelled), 2)
		self.assertEqual(sl_entry_cancelled[1].qty_after_transaction, exp_qty)
		self.assertEqual(sl_entry_cancelled[1].stock_value_difference, exp_amt)

		sa_gle = get_gle(doc.company, doc.name, "Stock Adjustment - _TC")
		self.assertEqual(sa_gle[0], sa_gle[1])

	def val_method_sl_entry(self, doc, expected_sle):
		sl_entries = get_sl_entries(doc.doctype, doc.name)

		for sle in sl_entries:
			self.assertEqual(expected_sle[sle.warehouse][0], sle.actual_qty)
			self.assertEqual(expected_sle[sle.warehouse][1], sle.qty_after_transaction)
			self.assertEqual(expected_sle[sle.warehouse][2], sle.stock_value_difference)
			self.assertEqual(expected_sle[sle.warehouse][3], sle.valuation_rate)
			self.assertEqual(expected_sle[sle.warehouse][4], sle.stock_queue)

	def check_gl_entry(self, doc, expected_values):
		gl_entries = get_gl_entries(doc.doctype, doc.name)

		self.assertTrue(gl_entries)

		for gle in gl_entries:
			self.assertEqual(expected_values[gle.account][0], gle.debit)
			self.assertEqual(expected_values[gle.account][1], gle.credit)

	def test_pr_ignore_pricing_rule_TC_B_050(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import (
			create_company_and_supplier as create_data,
		)

		get_company_supplier = create_data()
		company = get_company_supplier.get("child_company")
		supplier = get_company_supplier.get("supplier")
		target_warehouse = "Stores - TC-3"
		item_price = 130

		item = make_test_item("test_item_1")
		item.is_purchase_item = 1
		item.is_sales_item = 0
		item.save()

		if not frappe.db.exists("Item Price", {"item_code": item.item_code, "price_list": "Standard Buying"}):
			frappe.get_doc(
				{
					"doctype": "Item Price",
					"price_list": "Standard Buying",
					"item_code": item.item_code,
					"price_list_rate": item_price,
				}
			).insert()

		if not frappe.db.exists("Pricing Rule", {"title": "10% Discount"}):
			frappe.get_doc(
				{
					"doctype": "Pricing Rule",
					"title": "10% Discount",
					"company": company,
					"apply_on": "Item Code",
					"items": [{"item_code": item.item_code}],
					"rate_or_discount": "Discount Percentage",
					"discount_percentage": 10,
					"selling": 0,
					"buying": 1,
				}
			).insert()

		pr = frappe.get_doc(
			{
				"doctype": "Purchase Receipt",
				"supplier": supplier,
				"company": company,
				"posting_date": today(),
				"set_warehouse": target_warehouse,
				"items": [{"item_code": item.item_code, "warehouse": target_warehouse, "qty": 1}],
			}
		)
		pr.insert()
		self.assertEqual(len(pr.items), 1)
		self.assertEqual(pr.items[0].rate, 117)
		self.assertEqual(pr.items[0].discount_percentage, 10)
		pr.ignore_pricing_rule = 1
		pr.save()
		self.assertEqual(pr.items[0].rate, 130)
		self.assertEqual(pr.items[0].discount_percentage, 0)
		pr.submit()
		self.assertEqual(pr.docstatus, 1)
		self.assertEqual(pr.items[0].rate, 130)

	def test_pr_with_additional_discount_TC_B_056(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import (
			create_company_and_supplier as create_data,
		)

		get_company_supplier = create_data()
		company = get_company_supplier.get("child_company")
		supplier = get_company_supplier.get("supplier")
		target_warehouse = "Stores - TC-3"

		item_price = 10000
		item = make_test_item("testing_item_12")
		item.is_purchase_item = 1
		item.is_sales_item = 0
		item.save()

		pi = frappe.get_doc(
			{
				"doctype": "Purchase Receipt",
				"supplier": supplier,
				"company": company,
				"posting_date": today(),
				"set_warehouse": target_warehouse,
				"items": [
					{"item_code": item.item_code, "warehouse": target_warehouse, "qty": 1, "rate": item_price}
				],
			}
		)
		pi.insert(ignore_permissions=True)
		self.assertEqual(len(pi.items), 1)
		self.assertEqual(pi.items[0].rate, item_price)
		self.assertEqual(pi.net_total, item_price)
		pi.apply_discount_on = "Net Total"
		pi.additional_discount_percentage = 10
		pi.save()
		self.assertEqual(pi.discount_amount, 1000)
		self.assertEqual(pi.net_total, 9000)
		pi.submit()

	def test_putaway_rule_with_pr_pi_TC_B_153(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import (
			create_company_and_supplier as create_data,
		)

		get_company_supplier = create_data()
		company = get_company_supplier.get("child_company")
		supplier = get_company_supplier.get("supplier")
		warehouse = "Stores - TC-3"
		item = make_test_item("Test Item with Putaway Rule")

		if not frappe.db.exists("Putaway Rule", {"item_code": item.item_code, "warehouse": warehouse}):
			frappe.get_doc(
				{
					"company": company,
					"doctype": "Putaway Rule",
					"item_code": item.item_code,
					"warehouse": warehouse,
					"capacity": 20,
					"priority": 1,
				}
			).insert(ignore_if_duplicate=1)

		pr = frappe.get_doc(
			{
				"doctype": "Purchase Receipt",
				"supplier": supplier,
				"company": company,
				"currency": "INR",
				"items": [
					{
						"item_code": item.item_code,
						"qty": 20,
						"warehouse": warehouse,
					}
				],
				"apply_putaway_rule": 1,
			}
		)
		pr.insert()
		pr.submit()
		self.assertEqual(pr.docstatus, 1)
		stock_ledger_entries = frappe.get_all(
			"Stock Ledger Entry", filters={"voucher_no": pr.name}, fields=["warehouse", "actual_qty"]
		)

		warehouse_qty = sum(
			entry.actual_qty for entry in stock_ledger_entries if entry.warehouse == warehouse
		)
		self.assertEqual(warehouse_qty, 20)

		pi = make_purchase_invoice(pr.name)
		pi.bill_no = "test_bill_1122"
		pi.insert(ignore_permissions=True)
		pi.submit()
		self.assertEqual(pi.docstatus, 1)

	def test_pr_zero_valuation_TC_B_104(self):
		item = create_item("Testing-31")
		supplier = create_supplier(supplier_name="_Test Supplier")
		company = "_Test Company"
		if not frappe.db.exists("Company", company):
			company = frappe.new_doc("Company")
			company.company_name = company
			company.country = ("India",)
			company.default_currency = ("INR",)
			company.save()
		else:
			company = frappe.get_doc("Company", company)
		item_price = 0
		if not frappe.db.exists("Item Price", {"item_code": item.item_code, "price_list": "Standard Buying"}):
			frappe.get_doc(
				{
					"doctype": "Item Price",
					"price_list": "Standard Buying",
					"item_code": item.item_code,
					"price_list_rate": item_price,
				}
			).insert()
		pr_data = {
			"company": company.name,
			"item_code": item.item_code,
			"warehouse": create_warehouse("Stores - _TC", company=company.name),
			"supplier": supplier.name,
			"received_qty": 1,
			"qty": 1,
			"rate": 0,
			"do_not_save": 1,
		}
		pr = make_purchase_receipt(**pr_data)
		pr.items[0].allow_zero_valuation_rate = 1
		pr.save()
		pr.submit()
		gl_entries = get_gl_entries(pr.doctype, pr.name)
		self.assertEqual(len(gl_entries), 0)
		sle_entries = get_sl_entries(pr.doctype, pr.name)
		self.assertEqual(len(sle_entries), 1)

	def test_putaway_rule_with_pr_TC_B_154(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import (
			create_company_and_supplier as create_data,
		)

		get_company_supplier = create_data()
		company = get_company_supplier.get("child_company")
		supplier = get_company_supplier.get("supplier")
		warehouse = "Stores - TC-3"
		item = make_test_item("Test Item with Putaway Rule")

		if not frappe.db.exists("Putaway Rule", {"item_code": item.item_code, "warehouse": warehouse}):
			frappe.get_doc(
				{
					"company": company,
					"doctype": "Putaway Rule",
					"item_code": item.item_code,
					"warehouse": warehouse,
					"capacity": 20,
					"priority": 1,
				}
			).insert(ignore_if_duplicate=1)

		pr = frappe.get_doc(
			{
				"doctype": "Purchase Receipt",
				"supplier": supplier,
				"company": company,
				"items": [
					{
						"item_code": item.item_code,
						"qty": 20,
						"warehouse": warehouse,
					}
				],
				"apply_putaway_rule": 1,
			}
		)
		pr.insert()
		pr.submit()
		self.assertEqual(pr.docstatus, 1)

		stock_ledger_entries = frappe.get_all(
			"Stock Ledger Entry", filters={"voucher_no": pr.name}, fields=["warehouse", "actual_qty"]
		)

		warehouse_qty = sum(
			entry.actual_qty for entry in stock_ledger_entries if entry.warehouse == warehouse
		)
		self.assertEqual(warehouse_qty, 20)

	def test_pr_with_additional_discount_TC_B_053(self):
		company = "_Test Company"
		company_doc = frappe.get_doc("Company", company)
		if not company_doc.stock_received_but_not_billed:
			company_doc.stock_received_but_not_billed = "Stock Received But Not Billed - _TC"
			company_doc.save()
		# Scenario : PR => PI [With Additional Discount]
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import (
			make_purchase_invoice as make_pi_from_pr,
		)

		pr_data = {
			"company": "_Test Company",
			"item_code": "_Test Item",
			"warehouse": "Stores - _TC",
			"supplier": "_Test Supplier",
			"schedule_date": "2025-01-13",
			"qty": 1,
			"rate": 10000,
			"apply_discount_on": "Net Total",
			"additional_discount_percentage": 10,
			"do_not_submit": 1,
		}

		acc = frappe.new_doc("Account")
		acc.account_name = "Input Tax IGST"
		acc.parent_account = "Tax Assets - _TC"
		acc.company = "_Test Company"
		account_name = frappe.db.exists(
			"Account", {"account_name": "Input Tax IGST", "company": "_Test Company"}
		)
		if not account_name:
			account_name = acc.insert(ignore_permissions=True)

		doc_pr = make_purchase_receipt(**pr_data)
		doc_pr.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": account_name,
				"rate": 12,
				"description": "Input GST",
			},
		)
		doc_pr.submit()
		self.assertEqual(doc_pr.discount_amount, 1000)
		self.assertEqual(doc_pr.grand_total, 10080)

		pi = make_pi_from_pr(doc_pr.name)
		pi.insert(ignore_permissions=True)
		pi.submit()

		self.assertEqual(pi.discount_amount, 1000)
		self.assertEqual(pi.grand_total, 10080)

		# Accounting Ledger Checks
		pi_gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pi.name}, fields=["account", "debit", "credit"]
		)

		# PI Ledger Validation
		pi_total = sum(entry["debit"] for entry in pi_gl_entries)
		self.assertEqual(pi_total, 10080)

	def test_pr_to_pi_with_additional_discount_TC_B_059(self):
		company = "_Test Company"
		company_doc = frappe.get_doc("Company", company)
		if not company_doc.stock_received_but_not_billed:
			company_doc.stock_received_but_not_billed = "Stock Received But Not Billed - _TC"
			company_doc.save()
		# Scenario : PR => PI [With Applied Additional Discount on Grand Total]
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import (
			make_purchase_invoice as make_pi_from_pr,
		)

		pr_data = {
			"company": "_Test Company",
			"item_code": "_Test Item",
			"warehouse": "Stores - _TC",
			"supplier": "_Test Supplier",
			"schedule_date": "2025-01-13",
			"qty": 1,
			"rate": 10000,
			"apply_discount_on": "Grand Total",
			"additional_discount_percentage": 10,
			"do_not_submit": 1,
		}

		acc = frappe.new_doc("Account")
		acc.account_name = "Input Tax IGST"
		acc.parent_account = "Tax Assets - _TC"
		acc.company = "_Test Company"
		account_name = frappe.db.exists(
			"Account", {"account_name": "Input Tax IGST", "company": "_Test Company"}
		)
		if not account_name:
			account_name = acc.insert(ignore_permissions=True)

		doc_pr = make_purchase_receipt(**pr_data)
		doc_pr.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": account_name,
				"rate": 12,
				"description": "Input GST",
			},
		)
		doc_pr.submit()
		self.assertEqual(doc_pr.discount_amount, 1120)
		self.assertEqual(doc_pr.grand_total, 10080)

		pi = make_pi_from_pr(doc_pr.name)
		pi.insert(ignore_permissions=True)
		pi.submit()

		self.assertEqual(pi.discount_amount, 1120)
		self.assertEqual(pi.grand_total, 10080)

		# Accounting Ledger Checks
		pi_gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pi.name}, fields=["account", "debit", "credit"]
		)

		# PI Ledger Validation
		pi_total = sum(entry["debit"] for entry in pi_gl_entries)
		self.assertEqual(pi_total, 10080)

	def test_standalone_pr_with_additional_discount_TC_B_062(self):
		# Scenario : Standalone PR [With Applied Additional Discount on Grand Total]

		pr_data = {
			"company": "_Test Company",
			"item_code": "_Test Item",
			"warehouse": "Stores - _TC",
			"supplier": "_Test Supplier",
			"schedule_date": "2025-01-13",
			"qty": 1,
			"rate": 10000,
			"apply_discount_on": "Grand Total",
			"additional_discount_percentage": 10,
			"do_not_submit": 1,
		}

		acc = frappe.new_doc("Account")
		acc.account_name = "Input Tax IGST"
		acc.parent_account = "Tax Assets - _TC"
		acc.company = "_Test Company"
		account_name = frappe.db.exists(
			"Account", {"account_name": "Input Tax IGST", "company": "_Test Company"}
		)
		if not account_name:
			account_name = acc.insert(ignore_permissions=True)

		doc_pr = make_purchase_receipt(**pr_data)
		doc_pr.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": account_name,
				"rate": 12,
				"description": "Input GST",
			},
		)
		doc_pr.submit()
		self.assertEqual(doc_pr.discount_amount, 1120)
		self.assertEqual(doc_pr.grand_total, 10080)

	def test_pr_to_pi_with_return_TC_B_043(self):
		# Scenario : PR => PI => PI [Return]
		from erpnext.controllers.sales_and_purchase_return import make_return_doc
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import (
			make_purchase_invoice as make_pi_from_pr,
		)

		pr_data = {
			"company": "_Test Company",
			"item_code": "_Test Item",
			"warehouse": "Stores - _TC",
			"supplier": "_Test Supplier",
			"schedule_date": "2025-01-13",
			"qty": 1,
			"rate": 130,
		}

		doc_pr = make_purchase_receipt(**pr_data)
		self.assertEqual(doc_pr.docstatus, 1)

		doc_pi = make_pi_from_pr(doc_pr.name)
		doc_pi.insert()
		doc_pi.submit()

		doc_pi_return = make_return_doc(doc_pi.doctype, doc_pi.name)
		doc_pi_return.insert()
		doc_pi_return.submit()

		self.assertEqual(doc_pi_return.status, "Return")

	def test_stock_receipt_TC_SCK_223(self):
		if not frappe.db.exists("Company", "_Test Company"):
			company = frappe.new_doc("Company")
			company.company_name = "_Test Company"
			company.default_currency = "INR"
			company.insert()
		item_fields = {"item_name": "_Test Book", "is_stock_item": 1, "valuation_rate": 200}
		self.item_code = make_item("_Test Book", item_fields).name
		self.warehouse = create_warehouse("Stores", properties=None, company="_Test Company")
		self.qty_received = 10
		self.qty_issued = 5
		self.qty_reserved = 3
		self.company = "_Test Company"
		pr = make_purchase_receipt(item_code=self.item_code, qty=self.qty_received, warehouse=self.warehouse)
		pr.submit()
		stock_qty = get_stock_balance(self.item_code, self.warehouse)
		self.assertEqual(stock_qty, self.qty_received)

	def test_stock_issue_TC_SCK_223(self):
		if not frappe.db.exists("Company", "_Test Company"):
			company = frappe.new_doc("Company")
			company.company_name = "_Test Company"
			company.default_currency = "INR"
			company.insert()
		item_fields = {"item_name": "_Test Book", "is_stock_item": 1, "valuation_rate": 200}
		self.item_code = make_item("_Test Book", item_fields).name
		self.warehouse = create_warehouse("Stores", properties=None, company="_Test Company")
		self.qty_received = 10
		self.qty_issued = 5
		self.qty_reserved = 3
		self.company = "_Test Company"
		make_stock_entry(
			item_code=self.item_code,
			qty=self.qty_received,
			to_warehouse=self.warehouse,
			purpose="Material Receipt",
		)
		se = make_stock_entry(
			item_code=self.item_code,
			qty=self.qty_issued,
			from_warehouse=self.warehouse,
			purpose="Material Issue",
		)
		se.submit()
		stock_qty = get_stock_balance(self.item_code, self.warehouse)
		self.assertEqual(stock_qty, self.qty_received - self.qty_issued)

	def test_sales_order_reservation_TC_SCK_223(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company, create_customer

		create_company()
		create_item("_Test Item", warehouse="Stores - _TC")
		create_supplier(supplier_name="_Test Supplier")
		create_customer(name="Test Customer")

		frappe.db.set_value("Stock Settings", "Stock Settings", "enable_stock_reservation", 1)
		if not frappe.db.exists("Company", "_Test Company"):
			company = frappe.new_doc("Company")
			company.company_name = "_Test Company"
			company.default_currency = "INR"
			company.insert()
		item_fields = {"item_name": "_Test Book", "is_stock_item": 1, "valuation_rate": 200}
		self.item_code = make_item("_Test Book", item_fields).name
		self.warehouse = create_warehouse("Stores", properties=None, company="_Test Company")
		self.qty_received = 10
		self.qty_issued = 5
		self.qty_reserved = 3
		self.company = "_Test Company"
		so = frappe.get_doc(
			{
				"doctype": "Sales Order",
				"customer": "Test Customer",
				"delivery_date": today(),
				"company": "_Test Company",
				"items": [
					{"item_code": self.item_code, "qty": self.qty_reserved, "warehouse": self.warehouse}
				],
			}
		)
		so.insert()
		so.submit()
		reserved_qty = frappe.db.get_value(
			"Bin", {"item_code": self.item_code, "warehouse": self.warehouse}, "reserved_qty"
		)
		self.assertEqual(reserved_qty, self.qty_reserved)

	def test_purchase_receipt_submission_TC_SCK_147(self):
		"""Test Purchase Receipt Creation, Submission, and Stock Ledger Update"""

		# Create Purchase Receipt
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
		from erpnext.stock.utils import get_or_create_fiscal_year

		create_company()
		create_warehouse(
			warehouse_name="_Test Warehouse 1 - _TC",
			properties={"parent_warehouse": "All Warehouses - _TC"},
			company="_Test Company",
		)
		if not frappe.db.exists("Company", "_Test Company"):
			company = frappe.new_doc("Company")
			company.company_name = "_Test Company"
			company.default_currency = "INR"
			company.insert()

		item_fields = {
			"item_name": "Ball point Pen",
			"is_stock_item": 1,
			"stock_uom": "Box",
			"uoms": [{"uom": "Unit", "conversion_factor": 20}],
		}

		pr_fields = {
			"supplier": "Test Supplier 1",
			"posting_date": "03-01-2025",
			"item_code": "Ball point Pen",
			"qty": 5,
			"uom": "Box",
			"company": "_Test Company",
			"set_warehouse": "Stores - PP Ltd",
		}
		pr_data = {
			"company": "_Test Company",
			"item_code": "Ball point Pen",
			"warehouse": create_warehouse(
				"_Test Warehouse 1 - _TC",
				properties={"parent_warehouse": "All Warehouses - _TC"},
				company=pr_fields["company"],
			),
			"supplier": "Test Supplier 1",
			"schedule_date": "2025-02-03",
			"uom": "Unit",
			"stock_uom": "Box",
			"qty": 5,
		}
		get_or_create_fiscal_year("_Test Company")
		# target_warehouse = create_warehouse("_Test Warehouse", properties=None, company=pr_fields['company'])
		make_item("Ball point Pen", item_fields).name
		# self.item_code = "Ball Point Pen"
		create_supplier(
			supplier_name="Test Supplier 1", supplier_group="All Supplier Groups", supplier_type="Company"
		)

		doc_pr = make_purchase_receipt(**pr_data)

		sle = frappe.get_doc("Stock Ledger Entry", {"voucher_no": doc_pr.name})

		# Verify if stock ledger has the correct stock entry

		self.assertEqual(sle.qty_after_transaction, 5, "Stock Ledger did not update correctly!")

	def tearDown(self):
		"""Clean up test data after running the test"""
		frappe.db.rollback()  # Rollback changes to maintain a clean test environment

	def test_stock_reconciliation_TC_SCK_224(self):
		# self.item_code = "Book"
		self.warehouse = create_warehouse("Stores", properties=None, company="_Test Company")
		self.qty_received = 10
		self.qty_issued = 5
		self.qty_reserved = 3
		self.qty_reconciled = 8
		self.item_code = make_item(
			"Book", {"item_name": "Book", "valuation_rate": 500, "is_stock_item": 1}
		).name
		from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
			create_stock_reconciliation,
		)

		sr = create_stock_reconciliation(
			item_code=self.item_code, warehouse=self.warehouse, qty=self.qty_reconciled, rate=500
		)
		sr.submit()
		stock_qty = get_stock_balance(self.item_code, self.warehouse)
		self.assertEqual(stock_qty, self.qty_reconciled)

	def test_stock_ledger_report_TC_SCK_225(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
		from erpnext.stock.utils import get_or_create_fiscal_year

		create_company()
		item = []
		warehouse = []
		date = []

		get_or_create_fiscal_year("_Test Company")
		warehouse_new = create_warehouse("Stores", properties=None, company="_Test Company")
		item_code = make_item(
			"_Test Item225", {"item_name": "_Test Item225", "valuation_rate": 500, "is_stock_item": 1}
		).name
		se1 = make_stock_entry(
			item_code=item_code,
			qty=10,
			to_warehouse=warehouse_new,
			purpose="Material Receipt",
			do_not_submit=True,
		)
		se1.items[0].to_inv_site = "Site 1"
		se1.submit()

		from erpnext.stock.report.stock_ledger.stock_ledger import execute

		filters = frappe._dict(
			{  # Convert to allow dot notation
				"from_date": "2024-01-13",
				"to_date": "2025-12-12",
				"item_code": item_code,
				"warehouse": warehouse_new,
			}
		)

		columns, data = execute(filters)  # Unpacking the returned tuple

		# print(data)  # Debugging: Check report structure

		for i in range(1, len(data)):
			item.append(data[i]["item_code"])
			warehouse.append(data[i]["warehouse"])
			date.append(data[i]["posting_date"])
		item = set(item)
		item = list(item)
		warehouse = set(warehouse)
		warehouse = list(warehouse)

		self.assertTrue(filters["item_code"] == item[0], "Item tc failed")
		self.assertTrue(filters["warehouse"] == warehouse[0], "Warehouse tc failed")
		from_date = datetime.strptime(filters["from_date"], "%Y-%m-%d").date()
		to_date = datetime.strptime(filters["to_date"], "%Y-%m-%d").date()
		for i in date:
			self.assertTrue(from_date <= i <= to_date)

	def test_stock_ledger_report_TC_SCK_226(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
		from erpnext.stock.utils import get_or_create_fiscal_year

		create_company()
		item = []
		warehouse = []
		date = []
		get_or_create_fiscal_year("_Test Company")
		if not frappe.db.exists("Item Group", {"item_group_name": "_Test Group"}):
			item_group = frappe.new_doc("Item Group")
			item_group.item_group_name = "_Test Group"
			item_group.insert()
		warehouse_new = create_warehouse("Stores", properties=None, company="_Test Company")
		item_code = make_item(
			"_Test Item225",
			{
				"item_name": "_Test Item225",
				"valuation_rate": 500,
				"is_stock_item": 1,
				"item_group": "_Test Group",
			},
		).name
		se1 = make_stock_entry(
			item_code=item_code,
			qty=10,
			to_warehouse=warehouse_new,
			purpose="Material Receipt",
			do_not_submit=True,
		)
		se1.items[0].to_inv_site = "Site 1"
		se1.submit()

		from erpnext.stock.report.stock_ledger.stock_ledger import execute

		filters = frappe._dict(
			{  # Convert to allow dot notation
				"from_date": "2024-01-13",
				"to_date": "2025-12-12",
				"item_group": "_Test Group",
				"warehouse": warehouse_new,
			}
		)

		columns, data = execute(filters)  # Unpacking the returned tuple

		# print(data)  # Debugging: Check report structure

		for i in range(len(data)):
			item.append(data[i]["item_group"])
			warehouse.append(data[i]["warehouse"])
			date.append(data[i]["posting_date"])
		item = set(item)
		item = list(item)
		warehouse = set(warehouse)
		warehouse = list(warehouse)

		self.assertTrue(filters["item_group"] == item[0], "Item tc failed")
		self.assertTrue(filters["warehouse"] == warehouse[0], "Warehouse tc failed")
		from_date = datetime.strptime(filters["from_date"], "%Y-%m-%d").date()
		to_date = datetime.strptime(filters["to_date"], "%Y-%m-%d").date()
		for i in date:
			self.assertTrue(from_date <= i <= to_date)

	def test_po_required_TC_SCK_260(self):
		from frappe.exceptions import ValidationError

		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		# Backup and enforce PO Required setting
		original_setting = frappe.db.get_single_value("Buying Settings", "po_required")
		frappe.db.set_value("Buying Settings", None, "po_required", "Yes")

		# Create a Purchase Receipt
		pr = make_purchase_receipt(
			item_code="_Test Item", qty=1, rate=100, do_not_save=True, do_not_submit=True
		)

		# Manually clear purchase_order field to simulate missing PO
		pr.items[0].purchase_order = None
		with self.assertRaises(ValidationError) as context:
			pr.po_required()

		self.assertIn("Purchase Order number required for Item", str(context.exception))

		# Restore original setting
		frappe.db.set_value("Buying Settings", None, "po_required", original_setting)

	def test_validate_items_quality_inspection_TC_SCK_261(self):
		from frappe.exceptions import ValidationError

		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		company = setup_test_company_defaults()
		supplier = create_supplier(
			supplier_name="Test Supplier 1",
			supplier_group="All Supplier Groups",
			supplier_type="Company",
			default_currency="INR",
		)
		warehouse = frappe.get_all("Warehouse", filters={"company": company.name}, limit=1)[0].name
		item_code = make_item(
			"_Test Item225", {"item_name": "_Test Item225", "valuation_rate": 500, "is_stock_item": 1}
		).name

		# Create PR using helper (do not submit yet)
		pr = make_purchase_receipt(
			supplier=supplier.name,
			item_code=item_code,
			qty=1,
			rate=100,
			uom="Nos",
			stock_uom="Nos",
			warehouse=warehouse,
			do_not_submit=True,
			do_not_save=False,
			do_not_load=False,
		)

		assert frappe.db.exists("Purchase Receipt", pr.name), "PR not inserted properly"

		# Ensure Stock Settings field is available
		stock_settings_meta = frappe.get_meta("Stock Settings")
		if not stock_settings_meta.has_field("allow_to_make_quality_inspection_after_purchase_or_delivery"):
			print(
				"Skipping test: 'allow_to_make_quality_inspection_after_purchase_or_delivery' field missing."
			)
			return
		else:
			frappe.db.set_value(
				"Stock Settings", None, "allow_to_make_quality_inspection_after_purchase_or_delivery", 1
			)

		# Create initial Quality Inspection
		qi = frappe.get_doc(
			{
				"doctype": "Quality Inspection",
				"inspection_type": "Incoming",
				"item_code": "_Test Item",
				"reference_type": "Purchase Receipt",
				"reference_name": pr.name,
				"inspected_by": "Administrator",
				"sample_size": 1,
			}
		).insert(ignore_permissions=True)

		# Link wrong item in QI to trigger validation error
		qi.item_code = "Wrong Item"
		qi.save()

		# Attach QI to PR
		pr.reload()
		pr.items[0].quality_inspection = qi.name
		pr.items[0].item_code = "_Test Item"

		with self.assertRaises(ValidationError) as context:
			pr.validate_items_quality_inspection()
		self.assertIn("Item Code", str(context.exception))

		# Correct the item code and validate again
		qi.item_code = "_Test Item"
		qi.save()
		pr.validate_items_quality_inspection()

	def test_get_po_qty_and_warehouse_TC_SCK_262(self):
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		company = setup_test_company_defaults()
		supplier = create_supplier(
			supplier_name="Test Supplier 1",
			supplier_group="All Supplier Groups",
			supplier_type="Company",
			default_currency="INR",
		)
		item_code = make_item(
			"_Test Item225", {"item_name": "_Test Item225", "valuation_rate": 500, "is_stock_item": 1}
		).name
		warehouse = frappe.get_all("Warehouse", filters={"company": company.name}, limit=1)[0].name
		# Create PO
		po = create_purchase_order(
			supplier=supplier.name,
			company=company.name,
			item_code=item_code,
			qty=10,
			rate=100,
			warehouse=warehouse,
		)

		po_item = po.items[0]
		po_detail_name = po_item.name
		expected_qty = po_item.qty
		expected_warehouse = po_item.warehouse

		# Create a new PR
		pr = make_purchase_receipt(
			supplier=supplier,
			item_code=item_code,
			qty=1,
			rate=100,
			company=company.name,
			warehouse=warehouse,
			uom="Nos",
			stock_uom="Nos",
			do_not_submit=True,
			do_not_save=False,
			do_not_load=False,
		)

		qty, warehouse = pr.get_po_qty_and_warehouse(po_detail_name)

		# Assertions
		self.assertEqual(qty, expected_qty)
		self.assertEqual(warehouse, expected_warehouse)

	def test_make_item_gl_entries_TC_SCK_263(self):
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
		from erpnext.stock.doctype.landed_cost_voucher.test_landed_cost_voucher import (
			create_landed_cost_voucher,
		)
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import PurchaseReceipt
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		frappe.set_user("Administrator")

		# === Setup ===
		company = setup_test_company_defaults()

		self.gl_entries = []
		# Item Code create
		item_code = make_item(
			"_Test Item225", {"item_name": "_Test Item225", "valuation_rate": 500, "is_stock_item": 1}
		).name
		# Supplier Create
		supplier = create_supplier(
			supplier_name="Test Supplier 1",
			supplier_group="All Supplier Groups",
			supplier_type="Company",
			default_currency="INR",
		)

		# Warehouse Create
		warehouse = frappe.get_all("Warehouse", filters={"company": "_Test Company"}, limit=1)[0].name

		# Setup Fiscal Year GL Account & Cost center
		fiscal_year, expense_account, cost_center = setup_fy_gls_cost_center()

		# === CASE 1: Full Stock Item ===
		pi = make_purchase_invoice(
			item=item_code,
			qty=5,
			rate=100,
			warehouse=warehouse,
			company=company.name,
			supplier=supplier.name,
			do_not_submit=True,
			uom="Nos",
			expense_account=expense_account,
			cost_center=cost_center,
		)
		pi.posting_date = today()
		pi.due_date = today()
		pi.set_missing_values()
		pi.flags.ignore_validate = True
		pi.save()
		pi.submit()

		pr1 = make_purchase_receipt(
			supplier=supplier.name,
			item_code=item_code,
			qty=5,
			rate=100,
			stock_uom="Nos",
			warehouse=warehouse,
			do_not_submit=True,
		)
		pr1.items[0].valuation_rate = 100
		pr1.items[0].purchase_invoice = pi.name
		pr1.items[0].purchase_invoice_item = pi.items[0].name
		pr1.items[0].billed_amt = 500
		pr1.save()
		pr1.submit()

		PurchaseReceipt.make_item_gl_entries(
			pr1,
			self.gl_entries,
			warehouse_account={warehouse: {"account": "Stock Asset - _TC", "account_currency": "INR"}},
		)
		self.assertTrue(self.gl_entries)

		# === CASE 2: Non-Stock Item ===
		if not frappe.db.exists("Item", "_Test Non Stock Item"):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": "_Test Non Stock Item",
					"item_name": "Non Stock",
					"stock_uom": "Nos",
					"is_stock_item": 0,
					"is_purchase_item": 1,
					"gst_hsn_code": "84061000",
				}
			).insert()

		pr2 = make_purchase_receipt(
			supplier=supplier.name,
			item_code="_Test Non Stock Item",
			qty=1,
			rate=100,
			stock_uom="Nos",
			warehouse=warehouse,
			do_not_submit=True,
		)
		pr2.items[0].provisional_expense_account = expense_account
		pr2.save()
		pr2.submit()

		PurchaseReceipt.make_item_gl_entries(pr2, self.gl_entries, warehouse_account={})
		self.assertTrue(self.gl_entries)

		# === CASE 3: Warehouse with No Account Mapping ===
		new_warehouse = frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": "No Account Warehouse",
				"company": company.name,
			}
		).insert()

		pr3 = make_purchase_receipt(
			supplier=supplier.name,
			item_code=item_code,
			qty=2,
			rate=50,
			stock_uom="Nos",
			warehouse=new_warehouse.name,
			do_not_submit=True,
		)
		pr3.items[0].valuation_rate = 50
		pr3.save()
		pr3.submit()

		self.gl_entries.clear()
		PurchaseReceipt.make_item_gl_entries(
			pr3,
			self.gl_entries,
			warehouse_account={
				pr3.items[0].warehouse: {"account": "Stock Asset - _TC", "account_currency": "INR"}
			},
		)
		self.assertTrue(self.gl_entries)

		# === CASE 4: Landed Cost Voucher Entries ===
		from erpnext.accounts.doctype.account.test_account import create_account

		valuation_account = create_account(
			account_name="Expenses Included In Valuation",
			parent_account="Expenses - _TC",
			company="_Test Company",
		)

		stock_account = create_account(
			account_name="Stock Asset",
			parent_account="Current Assets - _TC",
			company="_Test Company",
			account_type="Stock",
		)

		pr4 = make_purchase_receipt(
			supplier=supplier.name,
			item_code=item_code,
			qty=10,
			rate=100,
			stock_uom="Nos",
			warehouse=warehouse,
			do_not_submit=True,
		)
		pr4.save()
		pr4.submit()

		# Create Landed Cost Voucher
		lcv = frappe.new_doc("Landed Cost Voucher")
		lcv.company = company.name
		lcv.distribute_charges_based_on = "Amount"

		lcv.append(
			"purchase_receipts",
			{
				"receipt_document_type": "Purchase Receipt",
				"receipt_document": pr4.name,
				"supplier": supplier.name,
				"posting_date": today(),
				"grand_total": 1000,
			},
		)

		lcv.append(
			"taxes",
			{
				"description": "Insurance Charges",
				"expense_account": valuation_account,
				"amount": 100,
				"included_in_valuation": 1,
			},
		)
		pr4.items[0].landed_cost_voucher_amount = 100
		lcv.insert()
		lcv.submit()

		self.gl_entries = []
		PurchaseReceipt.make_item_gl_entries(
			pr4,
			self.gl_entries,
			warehouse_account={warehouse: {"account": stock_account, "account_currency": "INR"}},
		)
		self.assertEqual(lcv.docstatus, 1, "Landed Cost Voucher submitted properly")

		for doc in [pr1, pr2, pr3, pr4, pi, lcv]:
			if doc.docstatus == 1:
				try:
					doc.cancel()
				except frappe.ValidationError:
					pass

	def test_get_billed_qty_against_purchase_receipt_TC_SCK_264(self):
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import (
			get_billed_qty_against_purchase_receipt,
			update_billing_percentage,
		)
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		# --- Setup ---
		frappe.set_user("Administrator")
		company = setup_test_company_defaults()
		supplier = create_supplier(
			supplier_name="Test Supplier 1",
			supplier_group="All Supplier Groups",
			supplier_type="Company",
			default_currency="INR",
		)
		# Item Code create
		item_code = make_item(
			"_Test Item225", {"item_name": "_Test Item225", "valuation_rate": 500, "is_stock_item": 1}
		).name
		warehouse = frappe.get_all("Warehouse", filters={"company": company.name}, limit=1)[0].name

		# Setup Fiscal Year GL Account & Cost center
		fiscal_year, expense_account, cost_center = setup_fy_gls_cost_center()

		# Create Purchase Receipt
		pr = make_purchase_receipt(
			item_code=item_code,
			qty=5,
			rate=100,
			uom="Nos",
			stock_uom="Nos",
			company=company.name,
			warehouse=warehouse,
			supplier=supplier.name,
		)
		pr_doc = frappe.get_doc("Purchase Receipt", pr.name)
		pr_item = pr_doc.items[0]

		# Create PI
		pi = make_purchase_invoice(
			item_code=pr_item.item_code,
			qty=3,
			rate=100,
			warehouse=pr_item.warehouse,
			do_not_submit=True,
			company=pr_doc.company,
			supplier=pr_doc.supplier,
			currency="INR",
			conversion_rate=1,
			uom="Nos",
			expense_account=expense_account,
			cost_center=cost_center,
		)
		# Link invoice item to Purchase Receipt
		pi.items[0].purchase_receipt = pr_doc.name
		pi.items[0].pr_detail = pr_item.name
		pi.set_missing_values()
		pi.save()
		pi.submit()

		# validate the function
		update_billing_percentage(pr_doc, update_modified=True, adjust_incoming_rate=True)
		billed_qty_map = get_billed_qty_against_purchase_receipt(pr_doc)
		self.assertIn(pr_item.name, billed_qty_map)
		self.assertEqual(billed_qty_map[pr_item.name], 3)

	def test_adjust_incoming_rate_for_pr_TC_SCK_265(self):
		from frappe.utils import flt

		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import adjust_incoming_rate_for_pr
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		frappe.set_user("Administrator")
		company = setup_test_company_defaults()
		supplier = create_supplier(
			supplier_name="Test Supplier 1",
			supplier_group="All Supplier Groups",
			supplier_type="Company",
			default_currency="INR",
		)
		item_code = make_item(
			"_Test Item225", {"item_name": "_Test Item225", "valuation_rate": 500, "is_stock_item": 1}
		).name
		warehouse = frappe.get_all("Warehouse", filters={"company": company.name}, limit=1)[0].name
		pr = make_purchase_receipt(
			item_code=item_code,
			qty=5,
			rate=120,
			uom="Nos",
			stock_uom="Nos",
			company=company.name,
			warehouse=warehouse,
			supplier=supplier.name,
			do_not_submit=True,
		)
		pr.reload()
		pr.items[0].rate = 120
		pr.items[0].valuation_rate = 120
		pr.items[0].save()
		adjust_incoming_rate_for_pr(pr)
		pr.reload()
		item_valuation = frappe.db.get_value("Purchase Receipt Item", pr.items[0].name, "valuation_rate")
		self.assertEqual(flt(item_valuation), 120)
		self.assertEqual(pr.doctype, "Purchase Receipt")

	def test_update_billed_amount_based_on_po_TC_SCK_266(self):
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import update_billed_amount_based_on_po
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		frappe.set_user("Administrator")
		item_code = make_item(
			"_Test Item225", {"item_name": "_Test Item225", "valuation_rate": 500, "is_stock_item": 1}
		).name
		company = setup_test_company_defaults()
		supplier = create_supplier(
			supplier_name="Test Supplier 1",
			supplier_group="All Supplier Groups",
			supplier_type="Company",
			default_currency="INR",
		)
		warehouse = frappe.get_all("Warehouse", filters={"company": company.name}, limit=1)[0].name
		fiscal_year, expense_account, cost_center = setup_fy_gls_cost_center()

		# Create PO for 10 qty
		po = create_purchase_order(
			item_code=item_code,
			qty=10,
			rate=100,
			company=company.name,
			supplier=supplier.name,
			warehouse=warehouse,
			do_not_submit=False,
		)
		po_item = po.items[0]

		# Create 2 PRs: one for 6, one for 4
		pr1 = make_purchase_receipt(
			purchase_order=po.name,
			item_code=item_code,
			qty=6,
			rate=100,
			uom="Nos",
			stock_uom="Nos",
			company=company.name,
			warehouse=warehouse,
			supplier=supplier.name,
			do_not_submit=False,
		)
		pr2 = make_purchase_receipt(
			purchase_order=po.name,
			item_code=item_code,
			qty=4,
			rate=100,
			uom="Nos",
			stock_uom="Nos",
			company=company.name,
			warehouse=warehouse,
			supplier=supplier.name,
			do_not_submit=False,
		)

		# Explicitly set purchase_order_item in PR items
		for pr in [pr1, pr2]:
			for item in pr.items:
				frappe.db.set_value("Purchase Receipt Item", item.name, "purchase_order_item", po_item.name)

		settings = frappe.get_doc("Repost Accounting Ledger Settings")
		# Check if Purchase Invoice is already allowed
		already_allowed = any(
			d.document_type == "Purchase Invoice" and d.allowed for d in settings.allowed_types
		)
		if not already_allowed:
			# Remove existing row for Purchase Invoice
			settings.allowed_types = [
				d for d in settings.allowed_types if d.document_type != "Purchase Invoice"
			]
			settings.append("allowed_types", {"document_type": "Purchase Invoice", "allowed": 1})
			settings.save()

		pi1 = make_purchase_invoice(
			purchase_order=po.name,
			purchase_receipt=pr1.name,
			pr_detail=pr1.items[0].name,
			item_code=item_code,
			qty=3,
			rate=100,
			uom="Nos",
			stock_uom="Nos",
			company=company.name,
			warehouse=warehouse,
			supplier=supplier.name,
			expense_account=expense_account,
			cost_center=cost_center,
			do_not_submit=True,
		)

		for item in pi1.items:
			item.po_detail = po_item.name
		pi1.save()
		pi1.submit()
		pi1.submit()

		pi2 = make_purchase_invoice(
			purchase_order=po.name,
			item_code=item_code,
			qty=5,
			rate=100,
			uom="Nos",
			stock_uom="Nos",
			company=company.name,
			warehouse=warehouse,
			supplier=supplier.name,
			expense_account=expense_account,
			cost_center=cost_center,
			do_not_submit=True,
		)

		for item in pi2.items:
			item.po_detail = po_item.name
		pi2.save()
		pi2.submit()

		po.reload()
		pr1.reload()
		pr2.reload()

		# Verify initial billed amounts
		self.assertEqual(po.items[0].billed_amt, 800.0)

		# Force update PO billed amount
		frappe.db.set_value("Purchase Order Item", po_item.name, "billed_amt", 800)

		# Debug: Check PR items linked to PO
		frappe.get_all(
			"Purchase Receipt Item",
			filters={"purchase_order_item": po_item.name},
			fields=["name", "parent", "purchase_order_item"],
		)

		po_details = [po_item.name]

		# Trigger update logic
		update_billed_amount_based_on_po(po_details, update_modified=True)
		pr1.reload()
		pr2.reload()

		# Verify billed amounts
		self.assertEqual(pr1.items[0].billed_amt, 600.0)
		self.assertEqual(pr2.items[0].billed_amt, 200.0)

		# Reset billed amounts for second test
		frappe.db.set_value("Purchase Receipt Item", pr1.items[0].name, "billed_amt", 0)
		frappe.db.set_value("Purchase Receipt Item", pr2.items[0].name, "billed_amt", 0)

		# Test 2: Update with pr_doc
		pr1_doc = frappe.get_doc("Purchase Receipt", pr1.name)
		updated = update_billed_amount_based_on_po(po_details, update_modified=True, pr_doc=pr1_doc)

		# Verify only pr1 was updated (since we passed pr_doc)
		self.assertIn(pr1.name, updated)

		# Verify billed amounts
		pr1.reload()
		pr2.reload()
		self.assertEqual(pr1.items[0].billed_amt, 600.0)

		# Finally update pr2 separately
		pr2_doc = frappe.get_doc("Purchase Receipt", pr2.name)
		update_billed_amount_based_on_po(po_details, update_modified=True, pr_doc=pr2_doc)
		pr2.reload()
		self.assertEqual(pr2.items[0].billed_amt, 200.0)

	def test_make_stock_entry_TC_SCK_267(self):
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_stock_entry

		"""Test basic stock entry creation from purchase receipt"""
		self.item = make_item(
			"_Test Stock Entry Item", {"is_stock_item": 1, "valuation_rate": 100, "stock_uom": "Nos"}
		).name

		company = setup_test_company_defaults()
		supplier = create_supplier(
			supplier_name="Test Supplier 1",
			supplier_group="All Supplier Groups",
			supplier_type="Company",
			default_currency="INR",
		)
		warehouse = frappe.get_all("Warehouse", filters={"company": company.name}, limit=1)[0].name
		fiscal_year, expense_account, cost_center = setup_fy_gls_cost_center()

		# Create Purchase Order
		self.po = create_purchase_order(
			item_code=self.item,
			qty=10,
			rate=100,
			supplier=supplier.name,
			warehouse=warehouse,
			company=company.name,
			do_not_submit=False,
		)

		# Create Purchase Receipt
		self.pr = make_purchase_receipt(
			purchase_order=self.po.name,
			item_code=self.item,
			qty=10,
			rate=100,
			uom="Nos",
			stock_uom="Nos",
			company=company.name,
			warehouse=warehouse,
			supplier=supplier.name,
			do_not_submit=False,
		)

		stock_entry = make_stock_entry(self.pr.name)

		# Verify Stock Entry fields
		self.assertEqual(stock_entry.stock_entry_type, "Material Transfer")
		self.assertEqual(stock_entry.purpose, "Material Transfer")
		self.assertEqual(len(stock_entry.items), 1)
		self.assertEqual(len(stock_entry.items), 1)

		# Verify item details
		item = stock_entry.items[0]
		self.assertEqual(item.item_code, self.item)
		self.assertEqual(item.qty, 10)
		self.assertEqual(item.s_warehouse, warehouse)
		self.assertEqual(item.reference_purchase_receipt, self.pr.name)

		# Verify docstatus
		self.assertEqual(stock_entry.docstatus, 0)

		# Cleanup
		if hasattr(self, "pr") and frappe.db.exists("Purchase Receipt", self.pr.name):
			self.pr.cancel()
		if hasattr(self, "po") and frappe.db.exists("Purchase Order", self.po.name):
			self.po.cancel()

	def test_get_invoiced_qty_map_TC_SCK_268(self):
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import get_invoiced_qty_map

		# Setup Item and Entities
		item_code = make_item(
			"_Test Item_501", {"is_stock_item": 1, "valuation_rate": 100, "stock_uom": "Nos"}
		).name

		company = setup_test_company_defaults()
		supplier = create_supplier(
			supplier_name="Test Supplier 501",
			supplier_group="All Supplier Groups",
			supplier_type="Company",
			default_currency="INR",
		)

		warehouse = frappe.get_all("Warehouse", filters={"company": company.name}, limit=1)[0].name
		fiscal_year, expense_account, cost_center = setup_fy_gls_cost_center()

		# Create PO and PR
		po = create_purchase_order(
			item_code=item_code,
			qty=10,
			rate=100,
			supplier=supplier.name,
			warehouse=warehouse,
			company=company.name,
			do_not_submit=False,
		)

		pr = make_purchase_receipt(
			purchase_order=po.name,
			item_code=item_code,
			qty=10,
			rate=100,
			uom="Nos",
			stock_uom="Nos",
			company=company.name,
			warehouse=warehouse,
			supplier=supplier.name,
			do_not_submit=False,
		)

		# Get Purchase Receipt Item reference (child table)
		pr_item = pr.items[0]

		# Create 2 Purchase Invoices for the same PR item
		pi1 = make_purchase_invoice(
			purchase_receipt=pr.name,
			qty=4,
			rate=100,
			item_code=item_code,
			uom="Nos",
			stock_uom="Nos",
			company=company.name,
			warehouse=warehouse,
			supplier=supplier.name,
			expense_account=expense_account,
			cost_center=cost_center,
			do_not_submit=True,
		)

		# Explicitly set pr_detail in PI items
		for item in pi1.items:
			item.pr_detail = pr_item.name
			item.purchase_receipt = pr.name
		pi1.save().submit()

		pi2 = make_purchase_invoice(
			purchase_receipt=pr.name,
			qty=6,
			rate=100,
			item_code=item_code,
			uom="Nos",
			stock_uom="Nos",
			company=company.name,
			warehouse=warehouse,
			supplier=supplier.name,
			expense_account=expense_account,
			cost_center=cost_center,
			do_not_submit=True,
		)

		# Explicitly set pr_detail in PI items
		for item in pi2.items:
			item.pr_detail = pr_item.name
			item.purchase_receipt = pr.name
		pi2.save().submit()

		# Run the method under test
		invoiced_qty_map = get_invoiced_qty_map(pr.name)

		# Assert the PR detail was added and quantity was aggregated (4 + 6 = 10)
		self.assertIn(pr_item.name, invoiced_qty_map)
		self.assertEqual(invoiced_qty_map[pr_item.name], 10)

		# Cleanup
		pi2.cancel()
		pi1.cancel()
		pr.reload()
		pr.cancel()
		po.reload()
		po.cancel()

	def test_get_already_received_qty_TC_SCK_455(self):
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
		from erpnext.regional.doctype.import_supplier_invoice.import_supplier_invoice import create_uom
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		# Setup
		item_code = make_item(
			"_Test Item_502", {"is_stock_item": 1, "valuation_rate": 100, "stock_uom": "Nos"}
		).name
		company = setup_test_company_defaults()
		supplier = create_supplier()
		create_uom("_Test UOM")
		create_warehouse("All Warehouses", {"company": company.name, "is_group": 1})
		suppiler_warehouse = create_warehouse("_Test Warehouse 1", {"company": company.name})

		warehouse = frappe.get_all("Warehouse", filters={"company": company.name}, limit=1)[0].name

		# Create PO with 10 qty
		po = create_purchase_order(
			item_code=item_code,
			qty=10,
			rate=100,
			supplier=supplier.name,
			warehouse=warehouse,
			company=company.name,
			do_not_submit=False,
		)
		po_item = po.items[0]

		# Create first PR with qty 4
		pr1 = make_purchase_receipt(
			purchase_order=po.name,
			item_code=item_code,
			qty=4,
			company=company.name,
			warehouse=warehouse,
			supplier=supplier.name,
			do_not_submit=False,
			rate=100,
			supplier_warehouse=suppiler_warehouse,
		)

		# Create second PR with qty 6 (this is where we'll call the method)
		pr2 = make_purchase_receipt(
			purchase_order=po.name,
			item_code=item_code,
			qty=6,
			company=company.name,
			warehouse=warehouse,
			supplier=supplier.name,
			do_not_submit=True,
			rate=100,
			supplier_warehouse=suppiler_warehouse,
		)
		pr2_item = pr2.items[0]

		# Ensure it's linked to the same PO item
		pr2_item.purchase_order_item = po_item.name
		pr2_item.purchase_order = po.name
		pr2.save()

		# Call method from pr2
		for item in pr1.items:
			frappe.db.set_value("Purchase Receipt Item", item.name, "purchase_order_item", po_item.name)
			frappe.db.set_value("Purchase Receipt Item", item.name, "purchase_order", po.name)

		already_received = pr2.get_already_received_qty(po.name, po_item.name)

		# Should only count pr1's qty, not pr2
		self.assertEqual(already_received, 4.0)

	def test_check_next_docstatus_TC_SCK_456(self):
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
		from erpnext.regional.doctype.import_supplier_invoice.import_supplier_invoice import create_uom
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		# Setup
		item_code = make_item(
			"_Test Item CheckNextDocStatus", {"is_stock_item": 1, "valuation_rate": 100, "stock_uom": "Nos"}
		).name

		company = setup_test_company_defaults()
		supplier = create_supplier()
		create_uom("_Test UOM")

		parent_account = ensure_parent_account("Parent Stock Account", company.name, company.abbr)
		w_account = create_account(
			account_name="Sub Stock Account",
			parent_account=parent_account,
			company=company.name,
			account_type="Stock",
			account_currency="INR",
		)

		supplier_warehouse = create_warehouse("_Test Warehouse 1", {"company": company.name})
		warehouse = create_warehouse("_Test Warehouse DocStatus", {"account": w_account}, company.name)

		# Create PO
		po = create_purchase_order(
			item_code=item_code,
			qty=5,
			rate=100,
			supplier=supplier.name,
			warehouse=warehouse,
			company=company.name,
			do_not_submit=False,
		)

		# Create PR
		pr = make_purchase_receipt(
			purchase_order=po.name,
			item_code=item_code,
			qty=5,
			rate=100,
			company=company.name,
			warehouse=warehouse,
			supplier=supplier.name,
			do_not_submit=False,
			supplier_warehouse=supplier_warehouse,
		)

		# Create and submit Purchase Invoice against PR
		pi = make_purchase_invoice(
			purchase_receipt=pr.name,
			qty=5,
			rate=100,
			item_code=item_code,
			uom="Nos",
			stock_uom="Nos",
			company=company.name,
			warehouse=warehouse,
			supplier=supplier.name,
			expense_account="Cost of Goods Sold - " + company.abbr,
			cost_center="Main - " + company.abbr,
			do_not_submit=True,
			supplier_warehouse=supplier_warehouse,
		)

		# Explicitly link PI to PR
		for item in pi.items:
			item.purchase_receipt = pr.name
			item.pr_detail = pr.items[0].name
		pi.save().submit()

		pr.submit_rv = frappe.db.sql(
			"""SELECT t1.name
			FROM `tabPurchase Invoice` t1, `tabPurchase Invoice Item` t2
			WHERE t1.name = t2.parent
			AND t2.purchase_receipt = %s
			AND t1.docstatus = 1""",
			(pr.name,),
		)

		# This should now raise ValidationError due to linked submitted PI
		with self.assertRaises(frappe.ValidationError) as cm:
			pr.check_next_docstatus()

		self.assertIn("already submitted", str(cm.exception))

	def test_make_item_gl_entries_creates_valid_gl_entries_TC_SCK_457(self):
		from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
		from erpnext.regional.doctype.import_supplier_invoice.import_supplier_invoice import create_uom

		company = setup_test_company_defaults()
		company.enable_perpetual_inventory = 1
		company.save()
		supplier = create_supplier()
		create_uom("_Test UOM")

		parent_account = ensure_parent_account("Parent Stock Account", company.name, company.abbr)
		w_account = create_account(
			account_name="Sub Stock Account",
			parent_account=parent_account,
			company=company.name,
			account_type="Stock",
			account_currency="INR",
		)

		create_warehouse("_Test Warehouse 1", {"company": company.name})
		item = make_item(
			"_Test GL Item",
			{"is_stock_item": 1, "valuation_rate": 100, "stock_uom": "Nos"},
		).name
		warehouse = create_warehouse("_Test GL Entry WH", {"account": w_account}, company.name)

		po = create_purchase_order(
			item_code=item,
			qty=10,
			rate=100,
			supplier=supplier.name,
			warehouse=warehouse,
			company=company.name,
			do_not_submit=False,
		)

		pr = make_purchase_receipt(po.name)

		pr.company = company.name
		pr.currency = "INR"
		pr.conversion_rate = 1.0
		pr.supplier = supplier.name
		pr.supplier_name = supplier.name
		pr.set_missing_values()
		pr.is_return = 0

		# Set explicit valuation rate on item
		for item in pr.items:
			item.valuation_rate = 100
			item.cost_center = company.default_cost_center

		pr.save()

		# Initialize
		gl_entries = []
		gl_entries = pr.get_gl_entries(
			warehouse_account=get_warehouse_account_map(company.name), via_landed_cost_voucher=False
		)
		self.assertTrue(gl_entries, msg="Expected GL entries to be generated by make_item_gl_entries")

	def test_is_landed_cost_booked_for_any_item_TC_SCK_458(self):
		from erpnext.regional.doctype.import_supplier_invoice.import_supplier_invoice import create_uom
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		item_code = make_item(
			"_Test Item_LCV_001",
			{
				"is_stock_item": 1,
				"stock_uom": "Nos",
				"valuation_rate": 100,
			},
		).name

		create_uom("_Test UOM")
		company = setup_test_company_defaults()
		supplier_warehouse = create_warehouse("_Test Warehouse 1", {"company": company.name})
		supplier = create_supplier()

		parent_account = ensure_parent_account("Parent Stock Account", company.name, company.abbr)
		w_account = create_account(
			account_name="Sub Stock Account",
			parent_account=parent_account,
			company=company.name,
			account_type="Stock",
			account_currency="INR",
		)

		warehouse = create_warehouse("_Test LCV Warehouse", {"account": w_account}, company.name)

		# PR without landed cost
		pr_no_lcv = make_purchase_receipt(
			item_code=item_code,
			qty=5,
			rate=100,
			company=company.name,
			warehouse=warehouse,
			supplier=supplier.name,
			do_not_submit=False,
			supplier_warehouse=supplier_warehouse,
		)
		self.assertFalse(pr_no_lcv.is_landed_cost_booked_for_any_item())

		# PR with landed cost
		pr_with_lcv = make_purchase_receipt(
			item_code=item_code,
			qty=5,
			rate=100,
			company=company.name,
			warehouse=warehouse,
			supplier=supplier.name,
			do_not_submit=True,
			supplier_warehouse=supplier_warehouse,
		)

		# Set and persist landed cost properly
		pr_with_lcv.items[0].landed_cost_voucher_amount = 500
		pr_with_lcv.save()
		frappe.db.set_value(
			"Purchase Receipt Item", pr_with_lcv.items[0].name, "landed_cost_voucher_amount", 500
		)
		pr_with_lcv.reload()

		self.assertTrue(pr_with_lcv.is_landed_cost_booked_for_any_item())

	def test_get_billed_qty_against_purchase_receipt_TC_SCK_459(self):
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import (
			get_billed_qty_against_purchase_receipt,
		)
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		company = setup_test_company_defaults()
		item_code = make_item(
			"_Test Item BRQ", {"is_stock_item": 1, "valuation_rate": 100, "stock_uom": "Nos"}
		).name
		supplier = create_supplier()

		parent_account = ensure_parent_account("Parent Stock Account", company.name, company.abbr)
		w_account = create_account(
			account_name="Sub Stock Account",
			parent_account=parent_account,
			company=company.name,
			account_type="Stock",
			account_currency="INR",
		)

		supplier_warehouse = create_warehouse("_Test Warehouse 1", {"company": company.name})
		warehouse = create_warehouse("_Test PR Warehouse", {"account": w_account}, company.name)

		# Create parent account if missing
		if not frappe.db.exists("Account", f"Expenses - {company.abbr}"):
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": "Expenses",
					"company": company,
					"root_type": "Expense",
					"is_group": 1,
				}
			).insert(ignore_mandatory=True)

		parent_name = f"Main - {company.abbr}"

		# If it exists, ensure it's marked as group
		if frappe.db.exists("Cost Center", parent_name):
			frappe.db.set_value("Cost Center", parent_name, "is_group", 1)
		else:
			# Create new group cost center
			frappe.get_doc(
				{"doctype": "Cost Center", "cost_center_name": "Main", "company": company, "is_group": 1}
			).insert()

		expense_account_name = f"_Test Account Cost for Goods Sold - {company.abbr}"
		if not frappe.db.exists("Account", expense_account_name):
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": "_Test Account Cost for Goods Sold",
					"company": company,
					"root_type": "Expense",
					"parent_account": f"Expenses - {company.abbr}",  # Adjust if parent doesn't exist
					"is_group": 0,
				}
			).insert(ignore_mandatory=True)

		# Ensure Cost Center
		cost_center_name = f"_Test Cost Center - {company.abbr}"
		if not frappe.db.exists("Cost Center", cost_center_name):
			frappe.get_doc(
				{
					"doctype": "Cost Center",
					"cost_center_name": "_Test Cost Center",
					"company": company,
					"is_group": 0,
					"parent_cost_center": f"Main - {company.abbr}",
				}
			).insert(ignore_mandatory=True)
		# Step 1: Create and Submit PR with 10 qty
		pr = make_purchase_receipt(
			item_code=item_code,
			qty=10,
			rate=100,
			company=company.name,
			warehouse=warehouse,
			supplier=supplier.name,
			do_not_submit=False,
			supplier_warehouse=supplier_warehouse,
			cost_center=cost_center_name,
		)

		pr_item_name = pr.items[0].name

		# Step 2: Create and Submit PI against 6 qty
		pi = make_purchase_invoice(
			purchase_receipt=pr.name,
			qty=6,
			rate=100,
			item_code=item_code,
			uom="Nos",
			stock_uom="Nos",
			company=company.name,
			warehouse=warehouse,
			supplier=supplier.name,
			do_not_submit=True,
			supplier_warehouse=supplier_warehouse,
			expense_account=expense_account_name,
			cost_center=cost_center_name,
		)
		for item in pi.items:
			item.pr_detail = pr_item_name
			item.purchase_receipt = pr.name
		pi.save().submit()

		# Step 3: Call the function and assert billed qty
		billed_qty_map = get_billed_qty_against_purchase_receipt(pr)

		assert pr_item_name in billed_qty_map
		assert billed_qty_map[pr_item_name] == 6.0

	def test_get_wbs_amount_TC_SCK_WBS_TC_SCK_460(self):
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import get_wbs_amount
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		# Setup data
		item_code = make_item(
			"_Test Item WBS", {"is_stock_item": 1, "stock_uom": "Nos", "valuation_rate": 100}
		).name

		company = setup_test_company_defaults()
		warehouse = create_warehouse("_Test WBS Warehouse", company=company.name)
		supplier = create_supplier()
		supplier_warehouse = create_warehouse("_Test Warehouse 1", {"company": company.name})

		# Create PR with WBS-tagged items
		pr = make_purchase_receipt(
			item_code=item_code,
			qty=2,
			rate=100,
			company=company.name,
			warehouse=warehouse,
			supplier=supplier.name,
			do_not_submit=True,
			supplier_warehouse=supplier_warehouse,
		)

		def create_wbs_structure(wbs_name, company):
			if not frappe.db.exists("Work Breakdown Structure", wbs_name):
				# Create a dummy project first (WBS requires one)
				project_name = f"Test Project for {wbs_name}"
				if not frappe.db.exists("Project", project_name):
					frappe.get_doc(
						{
							"doctype": "Project",
							"project_name": project_name,
							"company": company,
							"expected_start_date": frappe.utils.nowdate(),
						}
					).insert()

				wbs_doc = frappe.get_doc(
					{
						"doctype": "Work Breakdown Structure",
						"wbs_name": wbs_name,
						"project": project_name,
						"company": company,
						"is_group": 0,
					}
				).insert()
				return wbs_doc.name

			return wbs_name

		wbs_name1 = create_wbs_structure("WBS-001", company.name)
		wbs_name2 = create_wbs_structure("WBS-002", company.name)

		# Inject WBS into the PR items manually
		pr.items[0].work_breakdown_structure = wbs_name1
		pr.items[0].amount = 200
		pr.append(
			"items",
			{
				"item_code": item_code,
				"qty": 1,
				"rate": 100,
				"amount": 100,
				"warehouse": warehouse,
				"work_breakdown_structure": wbs_name1,
			},
		)
		pr.append(
			"items",
			{
				"item_code": item_code,
				"qty": 3,
				"rate": 100,
				"amount": 300,
				"warehouse": warehouse,
				"work_breakdown_structure": wbs_name2,
			},
		)
		pr.save()

		# Call real method on real Purchase Receipt
		self.assertEqual(get_wbs_amount(pr, wbs_name1), 300)
		self.assertEqual(get_wbs_amount(pr, wbs_name2), 300)
		self.assertEqual(get_wbs_amount(pr, "WBS-XYZ"), 0)

	def test_validate_available_budget_paths_TC_SCK_461(self):
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import (
			PurchaseReceipt,
			validate_available_budget,
		)

		company = setup_test_company_defaults().name

		def create_wbs_structure(wbs_name, company):
			if not frappe.db.exists("Work Breakdown Structure", wbs_name):
				# Create a dummy project first (WBS requires one)
				project_name = f"Test Project for {wbs_name}"
				if not frappe.db.exists("Project", project_name):
					frappe.get_doc(
						{
							"doctype": "Project",
							"project_name": project_name,
							"company": company,
							"expected_start_date": frappe.utils.nowdate(),
						}
					).insert()

				wbs_doc = frappe.get_doc(
					{
						"doctype": "Work Breakdown Structure",
						"wbs_name": wbs_name,
						"project": project_name,
						"company": company,
						"is_group": 0,
					}
				).insert()
				return wbs_doc.name

			return wbs_name

		# Setup 3 WBS structures for different paths
		wbs_ok = create_wbs_structure("WBS-OK", company)
		wbs_stop = create_wbs_structure("WBS-STOP", company)
		wbs_warn = create_wbs_structure("WBS-WARN", company)

		# Mock helper functions
		def fake_check_budget(wbs, amt, doctype, posting_date):
			if "STOP" in wbs:
				return {"available_bgt": -500, "action": "Stop", "wbs": wbs}
			elif "WARN" in wbs:
				return {"available_bgt": -300, "action": "Warn", "wbs": wbs}
			else:
				return {"available_bgt": 1000, "action": "Stop", "wbs": wbs}

		def fake_get_wbs_amount(self, wbs):
			return sum(i.amount for i in self.items if i.work_breakdown_structure == wbs)

		# Patch the functions
		PurchaseReceipt.get_wbs_amount = fake_get_wbs_amount
		import erpnext.stock.doctype.purchase_receipt.purchase_receipt as pr_module

		pr_module.check_available_budget = fake_check_budget

		def make_doc(wbs_list):
			doc = frappe.new_doc("Purchase Receipt")
			doc.company = company
			doc.posting_date = frappe.utils.today()
			for wbs in wbs_list:
				doc.append(
					"items",
					{
						"item_code": "_Test Item",
						"qty": 1,
						"rate": 100,
						"amount": 100,
						"work_breakdown_structure": wbs,
					},
				)
			return doc

		# Case 1: Single WBS, budget OK → no error
		doc = make_doc([wbs_ok])
		validate_available_budget(doc)

		# Case 2: Single WBS, budget exceeded, action = Stop → should throw
		doc = make_doc([wbs_stop])
		with self.assertRaises(frappe.ValidationError):
			validate_available_budget(doc)

		# Case 3: Single WBS, budget exceeded, action = Warn → should not throw
		doc = make_doc([wbs_warn])
		validate_available_budget(doc)

		# Case 4: Multiple WBS, one STOP → should throw
		doc = make_doc([wbs_ok, wbs_stop])
		with self.assertRaises(frappe.ValidationError):
			validate_available_budget(doc)

		# Case 5: Multiple WBS, all OK/WARN → should pass
		doc = make_doc([wbs_ok, wbs_warn])
		validate_available_budget(doc)

		# Case 6: No WBS → should pass
		doc = frappe.new_doc("Purchase Receipt")
		doc.company = company
		doc.append("items", {"item_code": "_Test Item", "qty": 1, "rate": 100, "amount": 100})
		validate_available_budget(doc)


def setup_test_company_defaults(company_name="_Test Company", abbreviation="_TC"):
	from frappe.defaults import set_default

	# Create Company if it doesn't exist
	if not frappe.db.exists("Company", company_name):
		frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": company_name,
				"abbr": abbreviation,
				"default_currency": "INR",
				"country": "India",
				"chart_of_accounts": "Standard",
			}
		).insert()

	company = frappe.get_doc("Company", company_name)

	# Create root account group if needed
	if not frappe.db.exists("Account", f"Application of Funds - {abbreviation}"):
		account = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "Application of Funds",
				"company": company_name,
				"root_type": "Asset",
				"is_group": 1,
			}
		)
		account.insert(ignore_mandatory=True)

	# Account helper
	def ensure_account(name, root_type="Asset"):
		full_name = f"{name} - {abbreviation}"
		if not frappe.db.exists("Account", full_name):
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": name,
					"company": company_name,
					"root_type": root_type,
					"parent_account": f"Application of Funds - {abbreviation}",
					"is_group": 0,
				}
			).insert()
		return full_name

	# Required Accounts
	accounts = {
		"default_receivable_account": ensure_account("Debtors", "Asset"),
		"default_payable_account": ensure_account("Creditors", "Liability"),
		"default_income_account": ensure_account("Sales", "Income"),
		"default_expense_account": ensure_account("Cost of Goods Sold", "Expense"),
		"stock_received_but_not_billed": ensure_account("Stock Received But Not Billed", "Liability"),
		"default_cash_account": ensure_account("Cash", "Asset"),
		"default_bank_account": ensure_account("Bank", "Asset"),
		"default_inventory_account": ensure_account("Stock Asset", "Asset"),
		"default_provisional_account": ensure_account("Cost of Goods Sold", "Expense"),
	}

	# Default Cost Center
	if not frappe.db.exists("Cost Center", f"Main - {abbreviation}"):
		frappe.get_doc(
			{"doctype": "Cost Center", "cost_center_name": "Main", "is_group": 0, "company": company_name}
		).insert()

	accounts["default_cost_center"] = f"Main - {abbreviation}"

	for field, value in accounts.items():
		company.set(field, value)

	company.enable_perpetual_inventory = 1
	company.enable_provisional_accounting_for_non_stock_items = 1
	company.save()

	set_default("company", company_name, "__default")

	return company


def setup_fy_gls_cost_center():
	company = setup_test_company_defaults()
	company_abbr = "_TC"
	# Setup GL Account COGS & Cost Center
	if not frappe.db.exists("Account", f"T Cost of Goods Sold - {company_abbr}"):
		frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "T Cost of Goods Sold",
				"parent_account": f"Expenses - {company_abbr}",
				"company": company,
				"is_group": 0,
			}
		).insert()
	if not frappe.db.exists("Cost Center", f"T Main - {company_abbr}"):
		frappe.get_doc(
			{
				"doctype": "Cost Center",
				"cost_center_name": "T Main",
				"parent_cost_center": f"{company.name} - {company_abbr}",
				"company": company,
				"is_group": 1,
			}
		).insert()
	if not frappe.db.exists("Cost Center", f"_Test Cost Center - {company_abbr}"):
		frappe.get_doc(
			{
				"doctype": "Cost Center",
				"cost_center_name": "_Test Cost Center",
				"parent_cost_center": f"T Main - {company_abbr}",
				"company": company.name,
				"is_group": 0,
			}
		).insert()

	current_date = datetime.today().date()

	matching_fy_list = frappe.get_all(
		"Fiscal Year",
		filters={
			"disabled": 0,
			"year_start_date": ["<=", current_date],
			"year_end_date": [">=", current_date],
		},
		fields=["name", "year_start_date", "year_end_date"],
	)
	is_company = False
	if len(matching_fy_list) > 0:
		for fy in matching_fy_list:
			fiscal_year = frappe.get_doc("Fiscal Year", fy["name"])
			for years in fiscal_year.companies:
				if years.company == company:
					is_company = True
					break
			if is_company:
				break

		if not is_company:
			for rows in matching_fy_list:
				try:
					fiscal_year = frappe.get_doc("Fiscal Year", rows.name)
					fiscal_year.append("companies", {"company": company})
					fiscal_year.save()
					break
				except Exception as e:
					print(f"Failed to get Fiscal Year {fy['name']}: {e}")
					continue

	else:
		# No fiscal year includes current date — create a new one
		current_year = current_date.year
		first_date = date(current_year, 1, 1)
		last_date = date(current_year, 12, 31)

		fiscal_year = frappe.new_doc("Fiscal Year")
		fiscal_year.year = f"{current_year}-{company}"
		fiscal_year.year_start_date = first_date
		fiscal_year.year_end_date = last_date
		fiscal_year.company = company  # Required to avoid overlap error
		fiscal_year.append("companies", {"company": company})
		fiscal_year.save()

	expense_account = f"T Cost of Goods Sold - {company_abbr}"
	cost_center = f"_Test Cost Center - {company_abbr}"
	return fiscal_year, expense_account, cost_center


def prepare_data_for_internal_transfer():
	from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_internal_supplier
	from erpnext.selling.doctype.customer.test_customer import create_internal_customer

	company = "_Test Company with perpetual inventory"

	create_internal_customer(
		"_Test Internal Customer 2",
		company,
		company,
	)

	create_internal_supplier(
		"_Test Internal Supplier 2",
		company,
		company,
	)

	if not frappe.db.get_value("Company", company, "unrealized_profit_loss_account"):
		account = "Unrealized Profit and Loss - TCP1"
		if not frappe.db.exists("Account", account):
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": "Unrealized Profit and Loss",
					"parent_account": "Direct Income - TCP1",
					"company": company,
					"is_group": 0,
					"account_type": "Income Account",
				}
			).insert()

		frappe.db.set_value("Company", company, "unrealized_profit_loss_account", account)


def get_sl_entries(voucher_type, voucher_no):
	return frappe.db.sql(
		""" select actual_qty,
		 warehouse,
		 stock_value_difference,
		 qty_after_transaction,
		 valuation_rate,
		 stock_queue
		from `tabStock Ledger Entry` where voucher_type=%s and voucher_no=%s
		order by posting_time desc""",
		(voucher_type, voucher_no),
		as_dict=1,
	)


def get_gl_entries(voucher_type, voucher_no, skip_cancelled=False, as_dict=True):
	gl = frappe.qb.DocType("GL Entry")
	gl_query = (
		frappe.qb.from_(gl)
		.select(
			gl.account,
			gl.debit,
			gl.credit,
			gl.cost_center,
		)
		.where((gl.voucher_type == voucher_type) & (gl.voucher_no == voucher_no))
		.orderby(gl.account, order=frappe.qb.desc)
	)
	if skip_cancelled:
		gl_query = gl_query.where(gl.is_cancelled == 0)
	else:
		gl_query = gl_query.select(gl.is_cancelled)
	return gl_query.run(as_dict=as_dict)


def get_taxes(**args):
	args = frappe._dict(args)

	return [
		{
			"account_head": "_Test Account Shipping Charges - TCP1",
			"add_deduct_tax": "Add",
			"category": "Valuation and Total",
			"charge_type": "Actual",
			"cost_center": args.cost_center or "Main - TCP1",
			"description": "Shipping Charges",
			"doctype": "Purchase Taxes and Charges",
			"parentfield": "taxes",
			"rate": 100.0,
			"tax_amount": 100.0,
		},
		{
			"account_head": "_Test Account VAT - TCP1",
			"add_deduct_tax": "Add",
			"category": "Total",
			"charge_type": "Actual",
			"cost_center": args.cost_center or "Main - TCP1",
			"description": "VAT",
			"doctype": "Purchase Taxes and Charges",
			"parentfield": "taxes",
			"rate": 120.0,
			"tax_amount": 120.0,
		},
		{
			"account_head": "_Test Account Customs Duty - TCP1",
			"add_deduct_tax": "Add",
			"category": "Valuation",
			"charge_type": "Actual",
			"cost_center": args.cost_center or "Main - TCP1",
			"description": "Customs Duty",
			"doctype": "Purchase Taxes and Charges",
			"parentfield": "taxes",
			"rate": 150.0,
			"tax_amount": 150.0,
		},
	]


def get_items(**args):
	args = frappe._dict(args)
	return [
		{
			"base_amount": 250.0,
			"conversion_factor": 1.0,
			"description": "_Test Item",
			"doctype": "Purchase Receipt Item",
			"item_code": "_Test Item",
			"item_name": "_Test Item",
			"parentfield": "items",
			"qty": 5.0,
			"rate": 50.0,
			"received_qty": 5.0,
			"rejected_qty": 0.0,
			"stock_uom": "_Test UOM",
			"uom": "_Test UOM",
			"warehouse": args.warehouse or "_Test Warehouse - _TC",
			"cost_center": args.cost_center or "Main - _TC",
		},
		{
			"base_amount": 250.0,
			"conversion_factor": 1.0,
			"description": "_Test Item Home Desktop 100",
			"doctype": "Purchase Receipt Item",
			"item_code": "_Test Item Home Desktop 100",
			"item_name": "_Test Item Home Desktop 100",
			"parentfield": "items",
			"qty": 5.0,
			"rate": 50.0,
			"received_qty": 5.0,
			"rejected_qty": 0.0,
			"stock_uom": "_Test UOM",
			"uom": "_Test UOM",
			"warehouse": args.warehouse or "_Test Warehouse 1 - _TC",
			"cost_center": args.cost_center or "Main - _TC",
		},
	]


def make_purchase_receipt(**args):
	if frappe.db.exists("DocType", "Location") and not frappe.db.exists("Location", "Test Location"):
		frappe.get_doc({"doctype": "Location", "location_name": "Test Location"}).insert()

	frappe.db.set_single_value("Buying Settings", "allow_multiple_items", 1)
	pr = frappe.new_doc("Purchase Receipt")
	args = frappe._dict(args)
	pr.posting_date = args.posting_date or today()
	if args.posting_time:
		pr.posting_time = args.posting_time
	if args.posting_date or args.posting_time:
		pr.set_posting_time = 1
	pr.company = args.company or "_Test Company"
	pr.supplier = args.supplier or "_Test Supplier"
	pr.is_subcontracted = args.is_subcontracted or 0
	pr.supplier_warehouse = args.supplier_warehouse or "_Test Warehouse 1 - _TC"
	pr.currency = args.currency or "INR"
	pr.is_return = args.is_return
	pr.return_against = args.return_against
	pr.apply_putaway_rule = args.apply_putaway_rule
	pr.additional_discount_percentage = args.additional_discount_percentage or None
	pr.apply_discount_on = args.apply_discount_on or None
	qty = args.qty if args.qty is not None else 5
	rejected_qty = args.rejected_qty or 0
	received_qty = args.received_qty or flt(rejected_qty) + flt(qty)

	item_code = args.item or args.item_code or "_Test Item"
	uom = args.uom or frappe.db.get_value("Item", item_code, "stock_uom") or "_Test UOM"

	bundle_id = None
	if not args.use_serial_batch_fields and (args.get("batch_no") or args.get("serial_no")):
		batches = {}
		if args.get("batch_no"):
			batches = frappe._dict({args.batch_no: qty})

		serial_nos = args.get("serial_no") or []

		bundle_id = make_serial_batch_bundle(
			frappe._dict(
				{
					"item_code": item_code,
					"warehouse": args.warehouse or "_Test Warehouse - _TC",
					"qty": qty,
					"batches": batches,
					"voucher_type": "Purchase Receipt",
					"serial_nos": serial_nos,
					"posting_date": args.posting_date or today(),
					"posting_time": args.posting_time,
					"do_not_submit": 1,
				}
			)
		).name

	pr.append(
		"items",
		{
			"item_code": item_code,
			"warehouse": args.warehouse or "_Test Warehouse - _TC",
			"qty": qty,
			"received_qty": received_qty,
			"rejected_qty": rejected_qty,
			"rejected_warehouse": args.rejected_warehouse or "_Test Rejected Warehouse - _TC"
			if rejected_qty != 0
			else "",
			"rate": args.rate if args.rate is not None else 50,
			"conversion_factor": args.conversion_factor or 1.0,
			"stock_qty": flt(qty) * (flt(args.conversion_factor) or 1.0),
			"serial_and_batch_bundle": bundle_id,
			"stock_uom": args.stock_uom or "_Test UOM",
			"uom": uom,
			"cost_center": args.cost_center or frappe.get_cached_value("Company", pr.company, "cost_center"),
			"asset_location": args.location or "Test Location",
			"use_serial_batch_fields": args.use_serial_batch_fields or 0,
			"serial_no": args.serial_no if args.use_serial_batch_fields else "",
			"batch_no": args.batch_no if args.use_serial_batch_fields else "",
		},
	)

	if args.get_multiple_items:
		pr.items = []

		company_cost_center = frappe.get_cached_value("Company", pr.company, "cost_center")
		cost_center = args.cost_center or company_cost_center

		for item in get_items(warehouse=args.warehouse, cost_center=cost_center):
			pr.append("items", item)

	if args.get_taxes_and_charges:
		for tax in get_taxes():
			pr.append("taxes", tax)

	if not args.do_not_save:
		pr.insert()
		if not args.do_not_submit:
			pr.submit()
		pr.load_from_db()

	return pr


def make_purchase_receipt_with_multiple_items(**args):
	if not frappe.db.exists("Location", "Test Location"):
		frappe.get_doc({"doctype": "Location", "location_name": "Test Location"}).insert()

	frappe.db.set_single_value("Buying Settings", "allow_multiple_items", 1)
	pr = frappe.new_doc("Purchase Receipt")
	args = frappe._dict(args)
	pr.posting_date = args.posting_date or today()
	if args.posting_time:
		pr.posting_time = args.posting_time
	if args.posting_date or args.posting_time:
		pr.set_posting_time = 1
	pr.company = args.company or "_Test Company"
	pr.supplier = args.supplier or "_Test Supplier"
	pr.is_subcontracted = args.is_subcontracted or 0
	pr.supplier_warehouse = args.supplier_warehouse or "_Test Warehouse 1 - _TC"
	pr.currency = args.currency or "INR"
	pr.is_return = args.is_return
	pr.return_against = args.return_against
	pr.apply_putaway_rule = args.apply_putaway_rule

	items = args["items"] or get_items(warehouse=args.warehouse, cost_center=args.cost_center)
	for item in items:
		if args.purchase_order:
			item["purchase_order"] = args.purchase_order
			pr.append("items", item)

	if args.get_taxes_and_charges:
		for tax in get_taxes():
			pr.append("taxes", tax)

	if not args.do_not_save:
		pr.insert()
		if not args.do_not_submit:
			pr.submit()
		pr.load_from_db()

	return pr


test_dependencies = ["BOM", "Item Price"]
if "Asset" in frappe.get_installed_apps():
	test_dependencies.append("Location")
test_records = frappe.get_test_records("Purchase Receipt")


def create_company(company):
	if not frappe.db.exists("Company", company):
		company_doc = frappe.new_doc("Company")
		company_doc.company_name = company
		company_doc.country = ("India",)
		company_doc.default_currency = ("INR",)
		company_doc.insert()


def ensure_parent_account(account_name, company, abbr, root_type="Asset", currency="INR"):
	if not frappe.db.exists("Account", {"account_name": account_name, "company": company}):
		parent_account = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": account_name,
				"is_group": 1,
				"company": company,
				"parent_account": f"Application of Funds (Assets) - {abbr}",
				"root_type": root_type,
				"account_currency": currency,
			}
		)
		parent_account.insert()
		return parent_account.name
	else:
		return frappe.db.get_value("Account", {"account_name": account_name, "company": company})
