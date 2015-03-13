# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import frappe
import json
import frappe.defaults
from frappe.utils import cint, nowdate, nowtime, cstr, add_days
from erpnext.stock.stock_ledger import get_previous_sle
from erpnext.accounts.utils import get_balance_on
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt \
	import get_gl_entries, set_perpetual_inventory
from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry, make_serialized_item
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos, SerialNoStatusError

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

		make_stock_entry(target="_Test Warehouse - _TC", qty=5, incoming_rate=100)
		
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
		frappe.db.set_value("Item", "_Test Item", "valuation_method", "FIFO")

		make_stock_entry(target="_Test Warehouse - _TC", qty=5, incoming_rate=100)

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
			qty=5, incoming_rate=100)

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

		make_stock_entry(item_code="_Test Item", target="_Test Warehouse - _TC", qty=10, incoming_rate=100)
		make_stock_entry(item_code="_Test Item Home Desktop 100", 
			target="_Test Warehouse - _TC", qty=10, incoming_rate=100)

		stock_in_hand_account = frappe.db.get_value("Account", {"warehouse": "_Test Warehouse - _TC"})
		prev_bal = get_balance_on(stock_in_hand_account)

		dn = create_delivery_note(item_code="_Test Sales BOM Item")
		
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
		self.assertEquals(bal, prev_bal - stock_value_diff)

		dn.cancel()
		self.assertFalse(get_gl_entries("Delivery Note", dn.name))

		set_perpetual_inventory(0)

	def test_serialized(self):
		se = make_serialized_item()
		serial_no = get_serial_nos(se.get("items")[0].serial_no)[0]

		dn = create_delivery_note(item_code="_Test Serialized Item With Series", serial_no=serial_no)

		self.check_serial_no_values(serial_no, {
			"status": "Delivered",
			"warehouse": "",
			"delivery_document_no": dn.name
		})

		dn.cancel()
		
		self.check_serial_no_values(serial_no, {
			"status": "Available",
			"warehouse": "_Test Warehouse - _TC",
			"delivery_document_no": ""
		})

	def test_serialize_status(self):
		se = make_serialized_item()
		serial_no = get_serial_nos(se.get("items")[0].serial_no)[0]
		
		frappe.db.set_value("Serial No", serial_no, "status", "Not Available")

		dn = create_delivery_note(item_code="_Test Serialized Item With Series", 
			serial_no=serial_no, do_not_submit=True)

		self.assertRaises(SerialNoStatusError, dn.submit)
		
	def check_serial_no_values(self, serial_no, field_values):
		for field, value in field_values.items():
			self.assertEquals(cstr(frappe.db.get_value("Serial No", serial_no, field)), value)


def create_delivery_note(**args):
	dn = frappe.new_doc("Delivery Note")
	args = frappe._dict(args)
	if args.posting_date:
		dn.posting_date = args.posting_date
	if args.posting_time:
		dn.posting_time = args.posting_time
	
	dn.company = args.company or "_Test Company"
	dn.customer = args.customer or "_Test Customer"
	
	dn.append("items", {
		"item_code": args.item or args.item_code or "_Test Item",
		"warehouse": args.warehouse or "_Test Warehouse - _TC",
		"qty": args.qty or 1,
		"rate": args.rate or 100,
		"conversion_factor": 1.0,
		"expense_account": "Cost of Goods Sold - _TC",
		"cost_center": "_Test Cost Center - _TC",
		"serial_no": args.serial_no
	})
	
	if not args.do_not_save:
		dn.insert()
		if not args.do_not_submit:
			dn.submit()
	return dn
	
test_dependencies = ["Sales BOM"]