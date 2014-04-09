# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import frappe
import frappe.defaults
from frappe.utils import cint
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import get_gl_entries, set_perpetual_inventory, test_records as pr_test_records

def _insert_purchase_receipt(item_code=None):
	if not item_code:
		item_code = pr_test_records[0]["purchase_receipt_details"][0]["item_code"]

	pr = frappe.copy_doc(pr_test_records[0])
	pr.get("purchase_receipt_details")[0].item_code = item_code
	pr.insert()
	pr.submit()

class TestDeliveryNote(unittest.TestCase):
	def test_over_billing_against_dn(self):
		self.clear_stock_account_balance()
		_insert_purchase_receipt()

		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice
		_insert_purchase_receipt()
		dn = frappe.copy_doc(test_records[0]).insert()

		self.assertRaises(frappe.ValidationError, make_sales_invoice,
			dn.name)

		dn = frappe.get_doc("Delivery Note", dn.name)
		dn.submit()
		si = make_sales_invoice(dn.name)

		self.assertEquals(len(si.get("entries")), len(dn.get("delivery_note_details")))

		# modify amount
		si.get("entries")[0].rate = 200
		self.assertRaises(frappe.ValidationError, frappe.get_doc(si).insert)


	def test_delivery_note_no_gl_entry(self):
		self.clear_stock_account_balance()
		set_perpetual_inventory(0)
		self.assertEqual(cint(frappe.defaults.get_global_default("auto_accounting_for_stock")), 0)

		_insert_purchase_receipt()

		dn = frappe.copy_doc(test_records[0])
		dn.insert()
		dn.submit()

		stock_value, stock_value_difference = frappe.db.get_value("Stock Ledger Entry",
			{"voucher_type": "Delivery Note", "voucher_no": dn.name,
				"item_code": "_Test Item"}, ["stock_value", "stock_value_difference"])
		self.assertEqual(stock_value, 0)
		self.assertEqual(stock_value_difference, -375)

		self.assertFalse(get_gl_entries("Delivery Note", dn.name))

	def test_delivery_note_gl_entry(self):
		self.clear_stock_account_balance()
		set_perpetual_inventory()
		self.assertEqual(cint(frappe.defaults.get_global_default("auto_accounting_for_stock")), 1)
		frappe.db.set_value("Item", "_Test Item", "valuation_method", "FIFO")

		_insert_purchase_receipt()

		dn = frappe.copy_doc(test_records[0])
		dn.get("delivery_note_details")[0].expense_account = "Cost of Goods Sold - _TC"
		dn.get("delivery_note_details")[0].cost_center = "Main - _TC"

		stock_in_hand_account = frappe.db.get_value("Account",
			{"master_name": dn.get("delivery_note_details")[0].warehouse})

		from erpnext.accounts.utils import get_balance_on
		prev_bal = get_balance_on(stock_in_hand_account, dn.posting_date)

		dn.insert()
		dn.submit()

		gl_entries = get_gl_entries("Delivery Note", dn.name)
		self.assertTrue(gl_entries)
		expected_values = {
			stock_in_hand_account: [0.0, 375.0],
			"Cost of Goods Sold - _TC": [375.0, 0.0]
		}
		for i, gle in enumerate(gl_entries):
			self.assertEquals([gle.debit, gle.credit], expected_values.get(gle.account))

		# check stock in hand balance
		bal = get_balance_on(stock_in_hand_account, dn.posting_date)
		self.assertEquals(bal, prev_bal - 375.0)

		# back dated purchase receipt
		pr = frappe.copy_doc(pr_test_records[0])
		pr.posting_date = "2013-01-01"
		pr.get("purchase_receipt_details")[0].rate = 100
		pr.get("purchase_receipt_details")[0].base_amount = 100

		pr.insert()
		pr.submit()

		gl_entries = get_gl_entries("Delivery Note", dn.name)
		self.assertTrue(gl_entries)
		expected_values = {
			stock_in_hand_account: [0.0, 666.67],
			"Cost of Goods Sold - _TC": [666.67, 0.0]
		}
		for i, gle in enumerate(gl_entries):
			self.assertEquals([gle.debit, gle.credit], expected_values.get(gle.account))

		dn.cancel()
		self.assertFalse(get_gl_entries("Delivery Note", dn.name))
		set_perpetual_inventory(0)

	def test_delivery_note_gl_entry_packing_item(self):
		self.clear_stock_account_balance()
		set_perpetual_inventory()

		_insert_purchase_receipt()
		_insert_purchase_receipt("_Test Item Home Desktop 100")

		dn = frappe.copy_doc(test_records[0])
		dn.get("delivery_note_details")[0].item_code = "_Test Sales BOM Item"
		dn.get("delivery_note_details")[0].qty = 1

		stock_in_hand_account = frappe.db.get_value("Account",
			{"master_name": dn.get("delivery_note_details")[0].warehouse})

		from erpnext.accounts.utils import get_balance_on
		prev_bal = get_balance_on(stock_in_hand_account, dn.posting_date)

		dn.insert()
		dn.submit()

		gl_entries = get_gl_entries("Delivery Note", dn.name)
		self.assertTrue(gl_entries)

		expected_values = {
			stock_in_hand_account: [0.0, 525],
			"Cost of Goods Sold - _TC": [525.0, 0.0]
		}
		for i, gle in enumerate(gl_entries):
			self.assertEquals([gle.debit, gle.credit], expected_values.get(gle.account))

		# check stock in hand balance
		bal = get_balance_on(stock_in_hand_account, dn.posting_date)
		self.assertEquals(bal, prev_bal - 525.0)

		dn.cancel()
		self.assertFalse(get_gl_entries("Delivery Note", dn.name))

		set_perpetual_inventory(0)

	def test_serialized(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_serialized_item
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		se = make_serialized_item()
		serial_nos = get_serial_nos(se.get("mtn_details")[0].serial_no)

		dn = frappe.copy_doc(test_records[0])
		dn.get("delivery_note_details")[0].item_code = "_Test Serialized Item With Series"
		dn.get("delivery_note_details")[0].qty = 1
		dn.get("delivery_note_details")[0].serial_no = serial_nos[0]
		dn.insert()
		dn.submit()

		self.assertEquals(frappe.db.get_value("Serial No", serial_nos[0], "status"), "Delivered")
		self.assertFalse(frappe.db.get_value("Serial No", serial_nos[0], "warehouse"))
		self.assertEquals(frappe.db.get_value("Serial No", serial_nos[0],
			"delivery_document_no"), dn.name)

		return dn

	def test_serialized_cancel(self):
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
		dn = self.test_serialized()
		dn.cancel()

		serial_nos = get_serial_nos(dn.get("delivery_note_details")[0].serial_no)

		self.assertEquals(frappe.db.get_value("Serial No", serial_nos[0], "status"), "Available")
		self.assertEquals(frappe.db.get_value("Serial No", serial_nos[0], "warehouse"), "_Test Warehouse - _TC")
		self.assertFalse(frappe.db.get_value("Serial No", serial_nos[0],
			"delivery_document_no"))

	def test_serialize_status(self):
		from erpnext.stock.doctype.serial_no.serial_no import SerialNoStatusError, get_serial_nos
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_serialized_item

		se = make_serialized_item()
		serial_nos = get_serial_nos(se.get("mtn_details")[0].serial_no)

		sr = frappe.get_doc("Serial No", serial_nos[0])
		sr.status = "Not Available"
		sr.save()

		dn = frappe.copy_doc(test_records[0])
		dn.get("delivery_note_details")[0].item_code = "_Test Serialized Item With Series"
		dn.get("delivery_note_details")[0].qty = 1
		dn.get("delivery_note_details")[0].serial_no = serial_nos[0]
		dn.insert()

		self.assertRaises(SerialNoStatusError, dn.submit)

	def clear_stock_account_balance(self):
		frappe.db.sql("""delete from `tabBin`""")
		frappe.db.sql("delete from `tabStock Ledger Entry`")
		frappe.db.sql("delete from `tabGL Entry`")

test_dependencies = ["Sales BOM"]

test_records = frappe.get_test_records('Delivery Note')
