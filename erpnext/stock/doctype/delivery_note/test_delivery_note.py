# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import frappe
import json
import frappe.defaults
from frappe.utils import cint, nowdate, nowtime, cstr, add_days, flt, today
from erpnext.stock.stock_ledger import get_previous_sle
from erpnext.accounts.utils import get_balance_on
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt \
	import get_gl_entries, set_perpetual_inventory
from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice
from erpnext.stock.doctype.stock_entry.test_stock_entry \
	import make_stock_entry, make_serialized_item, get_qty_after_transaction
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos, SerialNoWarehouseError
from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation \
	import create_stock_reconciliation, set_valuation_method
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order, create_dn_against_so

class TestDeliveryNote(unittest.TestCase):
	def test_over_billing_against_dn(self):
		frappe.db.set_value("Stock Settings", None, "allow_negative_stock", 1)

		dn = create_delivery_note(do_not_submit=True)
		self.assertRaises(frappe.ValidationError, make_sales_invoice, dn.name)

		dn.submit()
		si = make_sales_invoice(dn.name)
		self.assertEquals(len(si.get("items")), len(dn.get("items")))

		# modify amount
		si.get("items")[0].rate = 200
		self.assertRaises(frappe.ValidationError, frappe.get_doc(si).insert)

	def test_delivery_note_no_gl_entry(self):
		set_perpetual_inventory(0)
		self.assertEqual(cint(frappe.defaults.get_global_default("auto_accounting_for_stock")), 0)

		make_stock_entry(target="_Test Warehouse - _TC", qty=5, basic_rate=100)

		stock_queue = json.loads(get_previous_sle({
			"item_code": "_Test Item",
			"warehouse": "_Test Warehouse - _TC",
			"posting_date": nowdate(),
			"posting_time": nowtime()
		}).stock_queue or "[]")

		dn = create_delivery_note()

		sle = frappe.get_doc("Stock Ledger Entry", {"voucher_type": "Delivery Note", "voucher_no": dn.name})

		self.assertEqual(sle.stock_value_difference, -1*stock_queue[0][1])

		self.assertFalse(get_gl_entries("Delivery Note", dn.name))

	def test_delivery_note_gl_entry(self):
		set_perpetual_inventory()
		self.assertEqual(cint(frappe.defaults.get_global_default("auto_accounting_for_stock")), 1)
		set_valuation_method("_Test Item", "FIFO")

		make_stock_entry(target="_Test Warehouse - _TC", qty=5, basic_rate=100)

		stock_in_hand_account = frappe.db.get_value("Account", {"warehouse": "_Test Warehouse - _TC"})
		prev_bal = get_balance_on(stock_in_hand_account)

		dn = create_delivery_note()

		gl_entries = get_gl_entries("Delivery Note", dn.name)
		self.assertTrue(gl_entries)

		stock_value_difference = abs(frappe.db.get_value("Stock Ledger Entry",
			{"voucher_type": "Delivery Note", "voucher_no": dn.name}, "stock_value_difference"))

		expected_values = {
			stock_in_hand_account: [0.0, stock_value_difference],
			"Cost of Goods Sold - _TC": [stock_value_difference, 0.0]
		}
		for i, gle in enumerate(gl_entries):
			self.assertEquals([gle.debit, gle.credit], expected_values.get(gle.account))

		# check stock in hand balance
		bal = get_balance_on(stock_in_hand_account)
		self.assertEquals(bal, prev_bal - stock_value_difference)

		# back dated incoming entry
		make_stock_entry(posting_date=add_days(nowdate(), -2), target="_Test Warehouse - _TC",
			qty=5, basic_rate=100)

		gl_entries = get_gl_entries("Delivery Note", dn.name)
		self.assertTrue(gl_entries)

		stock_value_difference = abs(frappe.db.get_value("Stock Ledger Entry",
			{"voucher_type": "Delivery Note", "voucher_no": dn.name}, "stock_value_difference"))

		expected_values = {
			stock_in_hand_account: [0.0, stock_value_difference],
			"Cost of Goods Sold - _TC": [stock_value_difference, 0.0]
		}
		for i, gle in enumerate(gl_entries):
			self.assertEquals([gle.debit, gle.credit], expected_values.get(gle.account))

		dn.cancel()
		self.assertFalse(get_gl_entries("Delivery Note", dn.name))
		set_perpetual_inventory(0)

	def test_delivery_note_gl_entry_packing_item(self):
		set_perpetual_inventory()

		make_stock_entry(item_code="_Test Item", target="_Test Warehouse - _TC", qty=10, basic_rate=100)
		make_stock_entry(item_code="_Test Item Home Desktop 100",
			target="_Test Warehouse - _TC", qty=10, basic_rate=100)

		stock_in_hand_account = frappe.db.get_value("Account", {"warehouse": "_Test Warehouse - _TC"})
		prev_bal = get_balance_on(stock_in_hand_account)

		dn = create_delivery_note(item_code="_Test Product Bundle Item")

		stock_value_diff_rm1 = abs(frappe.db.get_value("Stock Ledger Entry",
			{"voucher_type": "Delivery Note", "voucher_no": dn.name, "item_code": "_Test Item"},
			"stock_value_difference"))

		stock_value_diff_rm2 = abs(frappe.db.get_value("Stock Ledger Entry",
			{"voucher_type": "Delivery Note", "voucher_no": dn.name,
				"item_code": "_Test Item Home Desktop 100"}, "stock_value_difference"))

		stock_value_diff = stock_value_diff_rm1 + stock_value_diff_rm2

		gl_entries = get_gl_entries("Delivery Note", dn.name)
		self.assertTrue(gl_entries)

		expected_values = {
			stock_in_hand_account: [0.0, stock_value_diff],
			"Cost of Goods Sold - _TC": [stock_value_diff, 0.0]
		}
		for i, gle in enumerate(gl_entries):
			self.assertEquals([gle.debit, gle.credit], expected_values.get(gle.account))

		# check stock in hand balance
		bal = get_balance_on(stock_in_hand_account)
		self.assertEquals(flt(bal, 2), flt(prev_bal - stock_value_diff, 2))

		dn.cancel()
		self.assertFalse(get_gl_entries("Delivery Note", dn.name))

		set_perpetual_inventory(0)

	def test_serialized(self):
		se = make_serialized_item()
		serial_no = get_serial_nos(se.get("items")[0].serial_no)[0]

		dn = create_delivery_note(item_code="_Test Serialized Item With Series", serial_no=serial_no)

		self.check_serial_no_values(serial_no, {
			"warehouse": "",
			"delivery_document_no": dn.name
		})

		dn.cancel()

		self.check_serial_no_values(serial_no, {
			"warehouse": "_Test Warehouse - _TC",
			"delivery_document_no": ""
		})

	def test_serialize_status(self):
		from frappe.model.naming import make_autoname
		serial_no = frappe.get_doc({
			"doctype": "Serial No",
			"item_code": "_Test Serialized Item With Series",
			"serial_no": make_autoname("SR", "Serial No")
		})
		serial_no.save()

		dn = create_delivery_note(item_code="_Test Serialized Item With Series",
			serial_no=serial_no.name, do_not_submit=True)

		self.assertRaises(SerialNoWarehouseError, dn.submit)

	def check_serial_no_values(self, serial_no, field_values):
		serial_no = frappe.get_doc("Serial No", serial_no)
		for field, value in field_values.items():
			self.assertEquals(cstr(serial_no.get(field)), value)

	def test_sales_return_for_non_bundled_items(self):
		set_perpetual_inventory()

		make_stock_entry(item_code="_Test Item", target="_Test Warehouse - _TC", qty=50, basic_rate=100)

		actual_qty_0 = get_qty_after_transaction()

		dn = create_delivery_note(qty=5, rate=500)

		actual_qty_1 = get_qty_after_transaction()
		self.assertEquals(actual_qty_0 - 5, actual_qty_1)

		# outgoing_rate
		outgoing_rate = frappe.db.get_value("Stock Ledger Entry", {"voucher_type": "Delivery Note",
			"voucher_no": dn.name}, "stock_value_difference") / 5

		# return entry
		dn1 = create_delivery_note(is_return=1, return_against=dn.name, qty=-2, rate=500)

		actual_qty_2 = get_qty_after_transaction()

		self.assertEquals(actual_qty_1 + 2, actual_qty_2)

		incoming_rate, stock_value_difference = frappe.db.get_value("Stock Ledger Entry",
			{"voucher_type": "Delivery Note", "voucher_no": dn1.name},
			["incoming_rate", "stock_value_difference"])

		self.assertEquals(flt(incoming_rate, 3), abs(flt(outgoing_rate, 3)))

		gle_warehouse_amount = frappe.db.get_value("GL Entry", {"voucher_type": "Delivery Note",
			"voucher_no": dn1.name, "account": "_Test Warehouse - _TC"}, "debit")

		self.assertEquals(gle_warehouse_amount, stock_value_difference)

		set_perpetual_inventory(0)

	def test_return_single_item_from_bundled_items(self):
		set_perpetual_inventory()

		create_stock_reconciliation(item_code="_Test Item", target="_Test Warehouse - _TC", qty=50, rate=100)
		create_stock_reconciliation(item_code="_Test Item Home Desktop 100", target="_Test Warehouse - _TC",
			qty=50, rate=100)

		dn = create_delivery_note(item_code="_Test Product Bundle Item", qty=5, rate=500)

		# Qty after delivery
		actual_qty_1 = get_qty_after_transaction()
		self.assertEquals(actual_qty_1,  25)

		# outgoing_rate
		outgoing_rate = frappe.db.get_value("Stock Ledger Entry", {"voucher_type": "Delivery Note",
			"voucher_no": dn.name, "item_code": "_Test Item"}, "stock_value_difference") / 25

		# return 'test item' from packed items
		dn1 = create_delivery_note(is_return=1, return_against=dn.name, qty=-10, rate=500)

		# qty after return
		actual_qty_2 = get_qty_after_transaction()
		self.assertEquals(actual_qty_2, 35)

		# Check incoming rate for return entry
		incoming_rate, stock_value_difference = frappe.db.get_value("Stock Ledger Entry",
			{"voucher_type": "Delivery Note", "voucher_no": dn1.name},
			["incoming_rate", "stock_value_difference"])

		self.assertEquals(flt(incoming_rate, 3), abs(flt(outgoing_rate, 3)))

		# Check gl entry for warehouse
		gle_warehouse_amount = frappe.db.get_value("GL Entry", {"voucher_type": "Delivery Note",
			"voucher_no": dn1.name, "account": "_Test Warehouse - _TC"}, "debit")

		self.assertEquals(gle_warehouse_amount, stock_value_difference)

		set_perpetual_inventory(0)

	def test_return_entire_bundled_items(self):
		set_perpetual_inventory()

		create_stock_reconciliation(item_code="_Test Item", target="_Test Warehouse - _TC", qty=50, rate=100)
		create_stock_reconciliation(item_code="_Test Item Home Desktop 100", target="_Test Warehouse - _TC",
			qty=50, rate=100)

		dn = create_delivery_note(item_code="_Test Product Bundle Item", qty=5, rate=500)

		#  return bundled item
		dn1 = create_delivery_note(item_code='_Test Product Bundle Item', is_return=1,
			return_against=dn.name, qty=-2, rate=500)

		# qty after return
		actual_qty = get_qty_after_transaction()
		self.assertEquals(actual_qty, 35)

		# Check incoming rate for return entry
		incoming_rate, stock_value_difference = frappe.db.get_value("Stock Ledger Entry",
			{"voucher_type": "Delivery Note", "voucher_no": dn1.name},
			["incoming_rate", "stock_value_difference"])

		self.assertEquals(incoming_rate, 100)

		# Check gl entry for warehouse
		gle_warehouse_amount = frappe.db.get_value("GL Entry", {"voucher_type": "Delivery Note",
			"voucher_no": dn1.name, "account": "_Test Warehouse - _TC"}, "debit")

		self.assertEquals(gle_warehouse_amount, 1400)

		set_perpetual_inventory(0)

	def test_return_for_serialized_items(self):
		se = make_serialized_item()
		serial_no = get_serial_nos(se.get("items")[0].serial_no)[0]

		dn = create_delivery_note(item_code="_Test Serialized Item With Series", rate=500, serial_no=serial_no)

		self.check_serial_no_values(serial_no, {
			"warehouse": "",
			"delivery_document_no": dn.name
		})

		# return entry
		dn1 = create_delivery_note(item_code="_Test Serialized Item With Series",
			is_return=1, return_against=dn.name, qty=-1, rate=500, serial_no=serial_no)

		self.check_serial_no_values(serial_no, {
			"warehouse": "_Test Warehouse - _TC",
			"delivery_document_no": ""
		})

		dn1.cancel()

		self.check_serial_no_values(serial_no, {
			"warehouse": "",
			"delivery_document_no": dn.name
		})

		dn.cancel()

		self.check_serial_no_values(serial_no, {
			"warehouse": "_Test Warehouse - _TC",
			"delivery_document_no": "",
			"purchase_document_no": se.name
		})

	def test_delivery_of_bundled_items_to_target_warehouse(self):
		set_perpetual_inventory()

		set_valuation_method("_Test Item", "FIFO")
		set_valuation_method("_Test Item Home Desktop 100", "FIFO")

		for warehouse in ("_Test Warehouse - _TC", "_Test Warehouse 1 - _TC"):
			create_stock_reconciliation(item_code="_Test Item", target=warehouse,
				qty=100, rate=100)
			create_stock_reconciliation(item_code="_Test Item Home Desktop 100",
				target=warehouse, qty=100, rate=100)

		opening_qty_test_warehouse_1 = get_qty_after_transaction(warehouse="_Test Warehouse 1 - _TC")

		dn = create_delivery_note(item_code="_Test Product Bundle Item",
			qty=5, rate=500, target_warehouse="_Test Warehouse 1 - _TC", do_not_submit=True)

		dn.submit()

		# qty after delivery
		actual_qty = get_qty_after_transaction(warehouse="_Test Warehouse - _TC")
		self.assertEquals(actual_qty, 75)

		actual_qty = get_qty_after_transaction(warehouse="_Test Warehouse 1 - _TC")
		self.assertEquals(actual_qty, opening_qty_test_warehouse_1 + 25)

		# stock value diff for source warehouse
		# for "_Test Item"
		stock_value_difference = frappe.db.get_value("Stock Ledger Entry",
			{"voucher_type": "Delivery Note", "voucher_no": dn.name,
				"item_code": "_Test Item", "warehouse": "_Test Warehouse - _TC"},
			"stock_value_difference")

		# stock value diff for target warehouse
		stock_value_difference1 = frappe.db.get_value("Stock Ledger Entry",
			{"voucher_type": "Delivery Note", "voucher_no": dn.name,
				"item_code": "_Test Item", "warehouse": "_Test Warehouse 1 - _TC"},
			"stock_value_difference")

		self.assertEquals(abs(stock_value_difference), stock_value_difference1)

		# for "_Test Item Home Desktop 100"
		stock_value_difference = frappe.db.get_value("Stock Ledger Entry",
			{"voucher_type": "Delivery Note", "voucher_no": dn.name,
				"item_code": "_Test Item Home Desktop 100", "warehouse": "_Test Warehouse - _TC"},
			"stock_value_difference")

		# stock value diff for target warehouse
		stock_value_difference1 = frappe.db.get_value("Stock Ledger Entry",
			{"voucher_type": "Delivery Note", "voucher_no": dn.name,
				"item_code": "_Test Item Home Desktop 100", "warehouse": "_Test Warehouse 1 - _TC"},
			"stock_value_difference")

		self.assertEquals(abs(stock_value_difference), stock_value_difference1)

		# Check gl entries
		gl_entries = get_gl_entries("Delivery Note", dn.name)
		self.assertTrue(gl_entries)

		stock_value_difference = abs(frappe.db.sql("""select sum(stock_value_difference)
			from `tabStock Ledger Entry` where voucher_type='Delivery Note' and voucher_no=%s
			and warehouse='_Test Warehouse - _TC'""", dn.name)[0][0])

		expected_values = {
			"_Test Warehouse - _TC": [0.0, stock_value_difference],
			"_Test Warehouse 1 - _TC": [stock_value_difference, 0.0]
		}
		for i, gle in enumerate(gl_entries):
			self.assertEquals([gle.debit, gle.credit], expected_values.get(gle.account))

		set_perpetual_inventory(0)

	def test_closed_delivery_note(self):
		from erpnext.stock.doctype.delivery_note.delivery_note import update_delivery_note_status

		dn = create_delivery_note(do_not_submit=True)
		dn.submit()

		update_delivery_note_status(dn.name, "Closed")
		self.assertEquals(frappe.db.get_value("Delivery Note", dn.name, "Status"), "Closed")

	def test_dn_billing_status_case1(self):
		# SO -> DN -> SI
		so = make_sales_order()
		dn = create_dn_against_so(so.name, delivered_qty=2)

		self.assertEqual(dn.status, "To Bill")
		self.assertEqual(dn.per_billed, 0)

		si = make_sales_invoice(dn.name)
		si.submit()

		dn.load_from_db()
		self.assertEqual(dn.get("items")[0].billed_amt, 200)
		self.assertEqual(dn.per_billed, 100)
		self.assertEqual(dn.status, "Completed")

	def test_dn_billing_status_case2(self):
		# SO -> SI and SO -> DN1, DN2
		from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note, make_sales_invoice

		so = make_sales_order()

		si = make_sales_invoice(so.name)
		si.get("items")[0].qty = 5
		si.insert()
		si.submit()

		frappe.db.set_value("Stock Settings", None, "allow_negative_stock", 1)

		dn1 = make_delivery_note(so.name)
		dn1.set_posting_time = 1
		dn1.posting_time = "10:00"
		dn1.get("items")[0].qty = 2
		dn1.submit()

		self.assertEqual(dn1.get("items")[0].billed_amt, 200)
		self.assertEqual(dn1.per_billed, 100)
		self.assertEqual(dn1.status, "Completed")

		dn2 = make_delivery_note(so.name)
		dn2.set_posting_time = 1
		dn2.posting_time = "08:00"
		dn2.get("items")[0].qty = 4
		dn2.submit()

		dn1.load_from_db()
		self.assertEqual(dn1.get("items")[0].billed_amt, 100)
		self.assertEqual(dn1.per_billed, 50)
		self.assertEqual(dn1.status, "To Bill")

		self.assertEqual(dn2.get("items")[0].billed_amt, 400)
		self.assertEqual(dn2.per_billed, 100)
		self.assertEqual(dn2.status, "Completed")

	def test_dn_billing_status_case3(self):
		# SO -> DN1 -> SI and SO -> SI and SO -> DN2
		from erpnext.selling.doctype.sales_order.sales_order \
			import make_delivery_note, make_sales_invoice as make_sales_invoice_from_so
		frappe.db.set_value("Stock Settings", None, "allow_negative_stock", 1)

		so = make_sales_order()

		dn1 = make_delivery_note(so.name)
		dn1.set_posting_time = 1
		dn1.posting_time = "10:00"
		dn1.get("items")[0].qty = 2
		dn1.submit()

		si1 = make_sales_invoice(dn1.name)
		si1.submit()

		dn1.load_from_db()
		self.assertEqual(dn1.per_billed, 100)

		si2 = make_sales_invoice_from_so(so.name)
		si2.get("items")[0].qty = 4
		si2.submit()

		dn2 = make_delivery_note(so.name)
		dn2.posting_time = "08:00"
		dn2.get("items")[0].qty = 5
		dn2.submit()

		dn1.load_from_db()
		self.assertEqual(dn1.get("items")[0].billed_amt, 200)
		self.assertEqual(dn1.per_billed, 100)
		self.assertEqual(dn1.status, "Completed")

		self.assertEqual(dn2.get("items")[0].billed_amt, 400)
		self.assertEqual(dn2.per_billed, 80)
		self.assertEqual(dn2.status, "To Bill")

	def test_dn_billing_status_case4(self):
		# SO -> SI -> DN
		from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_delivery_note

		so = make_sales_order()

		si = make_sales_invoice(so.name)
		si.submit()

		dn = make_delivery_note(si.name)
		dn.submit()

		self.assertEqual(dn.get("items")[0].billed_amt, 1000)
		self.assertEqual(dn.per_billed, 100)
		self.assertEqual(dn.status, "Completed")

def create_delivery_note(**args):
	dn = frappe.new_doc("Delivery Note")
	args = frappe._dict(args)
	dn.posting_date = args.posting_date or today()
	if args.posting_time:
		dn.posting_time = args.posting_time

	dn.company = args.company or "_Test Company"
	dn.customer = args.customer or "_Test Customer"
	dn.currency = args.currency or "INR"
	dn.is_return = args.is_return
	dn.return_against = args.return_against

	dn.append("items", {
		"item_code": args.item or args.item_code or "_Test Item",
		"warehouse": args.warehouse or "_Test Warehouse - _TC",
		"qty": args.qty or 1,
		"rate": args.rate or 100,
		"conversion_factor": 1.0,
		"expense_account": "Cost of Goods Sold - _TC",
		"cost_center": "_Test Cost Center - _TC",
		"serial_no": args.serial_no,
		"target_warehouse": args.target_warehouse
	})

	if not args.do_not_save:
		dn.insert()
		if not args.do_not_submit:
			dn.submit()
	return dn

test_dependencies = ["Product Bundle"]
