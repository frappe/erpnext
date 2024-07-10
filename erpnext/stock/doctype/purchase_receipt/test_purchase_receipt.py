# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import add_days, cint, cstr, flt, getdate, nowtime, today
from pypika import functions as fn

import erpnext
from erpnext.accounts.doctype.account.test_account import get_inventory_account
from erpnext.buying.doctype.supplier.test_supplier import create_supplier
from erpnext.controllers.buying_controller import QtyMismatchError
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
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse


class TestPurchaseReceipt(FrappeTestCase):
	def setUp(self):
		frappe.db.set_single_value("Buying Settings", "allow_multiple_items", 1)

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

	def test_auto_asset_creation(self):
		asset_item = "Test Asset Item"

		if not frappe.db.exists("Item", asset_item):
			asset_category = frappe.get_all("Asset Category")

			if asset_category:
				asset_category = asset_category[0].name

			if not asset_category:
				doc = frappe.get_doc(
					{
						"doctype": "Asset Category",
						"asset_category_name": "Test Asset Category",
						"depreciation_method": "Straight Line",
						"total_number_of_depreciations": 12,
						"frequency_of_depreciation": 1,
						"accounts": [
							{
								"company_name": "_Test Company",
								"fixed_asset_account": "_Test Fixed Asset - _TC",
								"accumulated_depreciation_account": "_Test Accumulated Depreciations - _TC",
								"depreciation_expense_account": "_Test Depreciations - _TC",
							}
						],
					}
				).insert()

				asset_category = doc.name

			item_data = make_item(
				asset_item,
				{
					"is_stock_item": 0,
					"stock_uom": "Box",
					"is_fixed_asset": 1,
					"auto_create_assets": 1,
					"asset_category": asset_category,
					"asset_naming_series": "ABC.###",
				},
			)
			asset_item = item_data.item_code

		pr = make_purchase_receipt(item_code=asset_item, qty=3)
		assets = frappe.db.get_all("Asset", filters={"purchase_receipt": pr.name})

		self.assertEqual(len(assets), 3)

		location = frappe.db.get_value("Asset", assets[0].name, "location")
		self.assertEqual(location, "Test Location")

		pr.cancel()

	def test_purchase_return_with_submitted_asset(self):
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_return

		pr = make_purchase_receipt(item_code="Test Asset Item", qty=1)

		asset = frappe.get_doc("Asset", {"purchase_receipt": pr.name})
		asset.available_for_use_date = frappe.utils.nowdate()
		asset.gross_purchase_amount = 50.0
		asset.append(
			"finance_books",
			{
				"expected_value_after_useful_life": 10,
				"depreciation_method": "Straight Line",
				"total_number_of_depreciations": 3,
				"frequency_of_depreciation": 1,
			},
		)
		asset.submit()

		pr_return = make_purchase_return(pr.name)
		self.assertRaises(frappe.exceptions.ValidationError, pr_return.submit)

		asset.load_from_db()
		asset.cancel()

		pr_return.submit()

		pr_return.cancel()
		pr.cancel()

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
		pi.insert()

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
		stock_diff = frappe.db.get_value(
			"Stock Ledger Entry",
			{
				"voucher_type": "Purchase Receipt",
				"voucher_no": pr.name,
				"is_cancelled": 0,
			},
			fieldname=["sum(stock_value_difference)"],
		)

		# Value of Stock Account should be equal to the sum of Stock Value Difference
		self.assertEqual(stock_account_value, stock_diff)

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
		)

		pr_return = make_purchase_return_against_rejected_warehouse(pr.name)
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
		amount = frappe.db.get_value("GL Entry", {"docstatus": 1, "voucher_no": pr.name}, ["sum(debit)"])
		expected_amount = pr.base_total
		self.assertEqual(amount, expected_amount)

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
		pi.insert()
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
		self.assertEqual(valuation_rate, 100)

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
		""" select actual_qty, warehouse, stock_value_difference
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
	qty = args.qty or 5
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


test_dependencies = ["BOM", "Item Price", "Location"]
test_records = frappe.get_test_records("Purchase Receipt")
