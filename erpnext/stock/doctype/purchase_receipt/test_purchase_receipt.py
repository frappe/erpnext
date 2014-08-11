# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import frappe
import frappe.defaults
from frappe.utils import cint

class TestPurchaseReceipt(unittest.TestCase):
	def test_make_purchase_invoice(self):
		self._clear_stock_account_balance()
		set_perpetual_inventory(0)
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice

		pr = frappe.copy_doc(test_records[0]).insert()

		self.assertRaises(frappe.ValidationError, make_purchase_invoice,
			pr.name)

		pr = frappe.get_doc("Purchase Receipt", pr.name)
		pr.submit()
		pi = make_purchase_invoice(pr.name)

		self.assertEquals(pi.doctype, "Purchase Invoice")
		self.assertEquals(len(pi.get("entries")), len(pr.get("purchase_receipt_details")))

		# modify rate
		pi.get("entries")[0].rate = 200
		self.assertRaises(frappe.ValidationError, frappe.get_doc(pi).submit)

	def test_purchase_receipt_no_gl_entry(self):
		self._clear_stock_account_balance()
		set_perpetual_inventory(0)
		pr = frappe.copy_doc(test_records[0])
		pr.insert()
		pr.submit()

		stock_value, stock_value_difference = frappe.db.get_value("Stock Ledger Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": pr.name,
				"item_code": "_Test Item", "warehouse": "_Test Warehouse - _TC"},
			["stock_value", "stock_value_difference"])
		self.assertEqual(stock_value, 375)
		self.assertEqual(stock_value_difference, 375)

		bin_stock_value = frappe.db.get_value("Bin", {"item_code": "_Test Item",
			"warehouse": "_Test Warehouse - _TC"}, "stock_value")
		self.assertEqual(bin_stock_value, 375)

		self.assertFalse(get_gl_entries("Purchase Receipt", pr.name))

	def test_purchase_receipt_gl_entry(self):
		self._clear_stock_account_balance()

		set_perpetual_inventory()
		self.assertEqual(cint(frappe.defaults.get_global_default("auto_accounting_for_stock")), 1)
		pr = frappe.copy_doc(test_records[0])
		pr.insert()
		pr.submit()

		gl_entries = get_gl_entries("Purchase Receipt", pr.name)

		self.assertTrue(gl_entries)

		stock_in_hand_account = frappe.db.get_value("Account",
			{"master_name": pr.get("purchase_receipt_details")[0].warehouse})
		fixed_asset_account = frappe.db.get_value("Account",
			{"master_name": pr.get("purchase_receipt_details")[1].warehouse})

		expected_values = {
			stock_in_hand_account: [375.0, 0.0],
			fixed_asset_account: [375.0, 0.0],
			"Stock Received But Not Billed - _TC": [0.0, 500.0],
			"Expenses Included In Valuation - _TC": [0.0, 250.0]
		}

		for gle in gl_entries:
			self.assertEquals(expected_values[gle.account][0], gle.debit)
			self.assertEquals(expected_values[gle.account][1], gle.credit)

		pr.cancel()
		self.assertFalse(get_gl_entries("Purchase Receipt", pr.name))

		set_perpetual_inventory(0)

	def _clear_stock_account_balance(self):
		frappe.db.sql("delete from `tabStock Ledger Entry`")
		frappe.db.sql("""delete from `tabBin`""")
		frappe.db.sql("""delete from `tabGL Entry`""")

	def test_subcontracting(self):
		pr = frappe.copy_doc(test_records[1])
		pr.run_method("calculate_taxes_and_totals")
		pr.insert()

		self.assertEquals(len(pr.get("pr_raw_material_details")), 2)
		self.assertEquals(pr.get("purchase_receipt_details")[0].rm_supp_cost, 70000.0)


	def test_serial_no_supplier(self):
		pr = frappe.copy_doc(test_records[0])
		pr.get("purchase_receipt_details")[0].item_code = "_Test Serialized Item With Series"
		pr.get("purchase_receipt_details")[0].qty = 1
		pr.get("purchase_receipt_details")[0].received_qty = 1
		pr.insert()
		pr.submit()

		self.assertEquals(frappe.db.get_value("Serial No", pr.get("purchase_receipt_details")[0].serial_no,
			"supplier"), pr.supplier)

		return pr

	def test_serial_no_cancel(self):
		pr = self.test_serial_no_supplier()
		pr.cancel()

		self.assertFalse(frappe.db.get_value("Serial No", pr.get("purchase_receipt_details")[0].serial_no,
			"warehouse"))

	def test_rejected_serial_no(self):
		pr = frappe.copy_doc(test_records[0])
		pr.get("purchase_receipt_details")[0].item_code = "_Test Serialized Item With Series"
		pr.get("purchase_receipt_details")[0].qty = 3
		pr.get("purchase_receipt_details")[0].rejected_qty = 2
		pr.get("purchase_receipt_details")[0].received_qty = 5
		pr.get("purchase_receipt_details")[0].rejected_warehouse = "_Test Rejected Warehouse - _TC"
		pr.insert()
		pr.submit()

		accepted_serial_nos = pr.get("purchase_receipt_details")[0].serial_no.split("\n")
		self.assertEquals(len(accepted_serial_nos), 3)
		for serial_no in accepted_serial_nos:
			self.assertEquals(frappe.db.get_value("Serial No", serial_no, "warehouse"),
				pr.get("purchase_receipt_details")[0].warehouse)

		rejected_serial_nos = pr.get("purchase_receipt_details")[0].rejected_serial_no.split("\n")
		self.assertEquals(len(rejected_serial_nos), 2)
		for serial_no in rejected_serial_nos:
			self.assertEquals(frappe.db.get_value("Serial No", serial_no, "warehouse"),
				pr.get("purchase_receipt_details")[0].rejected_warehouse)

def get_gl_entries(voucher_type, voucher_no):
	return frappe.db.sql("""select account, debit, credit
		from `tabGL Entry` where voucher_type=%s and voucher_no=%s
		order by account desc""", (voucher_type, voucher_no), as_dict=1)

def set_perpetual_inventory(enable=1):
	accounts_settings = frappe.get_doc("Accounts Settings")
	accounts_settings.auto_accounting_for_stock = enable
	accounts_settings.save()


test_dependencies = ["BOM"]

test_records = frappe.get_test_records('Purchase Receipt')
