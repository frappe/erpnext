# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import frappe
import frappe.defaults
from frappe.utils import cint, flt

class TestPurchaseReceipt(unittest.TestCase):
	def test_make_purchase_invoice(self):
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice

		pr = make_purchase_receipt(do_not_save=True)
		self.assertRaises(frappe.ValidationError, make_purchase_invoice, pr.name)
		pr.submit()

		pi = make_purchase_invoice(pr.name)

		self.assertEquals(pi.doctype, "Purchase Invoice")
		self.assertEquals(len(pi.get("items")), len(pr.get("items")))

		# modify rate
		pi.get("items")[0].rate = 200
		self.assertRaises(frappe.ValidationError, frappe.get_doc(pi).submit)

	def test_purchase_receipt_no_gl_entry(self):
		set_perpetual_inventory(0)
		
		existing_bin_stock_value = frappe.db.get_value("Bin", {"item_code": "_Test Item",
			"warehouse": "_Test Warehouse - _TC"}, "stock_value")
		
		pr = make_purchase_receipt()

		stock_value_difference = frappe.db.get_value("Stock Ledger Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": pr.name,
				"item_code": "_Test Item", "warehouse": "_Test Warehouse - _TC"}, "stock_value_difference")

		self.assertEqual(stock_value_difference, 250)

		current_bin_stock_value = frappe.db.get_value("Bin", {"item_code": "_Test Item",
			"warehouse": "_Test Warehouse - _TC"}, "stock_value")
		self.assertEqual(current_bin_stock_value, existing_bin_stock_value + 250)

		self.assertFalse(get_gl_entries("Purchase Receipt", pr.name))

	def test_purchase_receipt_gl_entry(self):
		set_perpetual_inventory()
		self.assertEqual(cint(frappe.defaults.get_global_default("auto_accounting_for_stock")), 1)
		pr = frappe.copy_doc(test_records[0])
		pr.insert()
		pr.submit()

		gl_entries = get_gl_entries("Purchase Receipt", pr.name)

		self.assertTrue(gl_entries)

		stock_in_hand_account = frappe.db.get_value("Account",
			{"warehouse": pr.get("items")[0].warehouse})
		fixed_asset_account = frappe.db.get_value("Account",
			{"warehouse": pr.get("items")[1].warehouse})

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

	def test_subcontracting(self):
		pr = make_purchase_receipt(item_code="_Test FG Item", qty=10, rate=500, is_subcontracted="Yes")
		self.assertEquals(len(pr.get("supplied_items")), 2)
		
		rm_supp_cost = sum([d.amount for d in pr.get("supplied_items")])
		self.assertEquals(pr.get("items")[0].rm_supp_cost, flt(rm_supp_cost, 2))

	def test_serial_no_supplier(self):
		pr = make_purchase_receipt(item_code="_Test Serialized Item With Series", qty=1)
		self.assertEquals(frappe.db.get_value("Serial No", pr.get("items")[0].serial_no, "supplier"), 
			pr.supplier)
		
		pr.cancel()
		self.assertFalse(frappe.db.get_value("Serial No", pr.get("items")[0].serial_no, "warehouse"))

	def test_rejected_serial_no(self):
		pr = frappe.copy_doc(test_records[0])
		pr.get("items")[0].item_code = "_Test Serialized Item With Series"
		pr.get("items")[0].qty = 3
		pr.get("items")[0].rejected_qty = 2
		pr.get("items")[0].received_qty = 5
		pr.get("items")[0].rejected_warehouse = "_Test Rejected Warehouse - _TC"
		pr.insert()
		pr.submit()

		accepted_serial_nos = pr.get("items")[0].serial_no.split("\n")
		self.assertEquals(len(accepted_serial_nos), 3)
		for serial_no in accepted_serial_nos:
			self.assertEquals(frappe.db.get_value("Serial No", serial_no, "warehouse"),
				pr.get("items")[0].warehouse)

		rejected_serial_nos = pr.get("items")[0].rejected_serial_no.split("\n")
		self.assertEquals(len(rejected_serial_nos), 2)
		for serial_no in rejected_serial_nos:
			self.assertEquals(frappe.db.get_value("Serial No", serial_no, "warehouse"),
				pr.get("items")[0].rejected_warehouse)

def get_gl_entries(voucher_type, voucher_no):
	return frappe.db.sql("""select account, debit, credit
		from `tabGL Entry` where voucher_type=%s and voucher_no=%s
		order by account desc""", (voucher_type, voucher_no), as_dict=1)

def set_perpetual_inventory(enable=1):
	accounts_settings = frappe.get_doc("Accounts Settings")
	accounts_settings.auto_accounting_for_stock = enable
	accounts_settings.save()
	
def make_purchase_receipt(**args):
	pr = frappe.new_doc("Purchase Receipt")
	args = frappe._dict(args)
	if args.posting_date:
		pr.posting_date = args.posting_date
	if args.posting_time:
		pr.posting_time = args.posting_time
	pr.company = args.company or "_Test Company"
	pr.supplier = args.supplier or "_Test Supplier"
	pr.is_subcontracted = args.is_subcontracted or "No"
	pr.supplier_warehouse = "_Test Warehouse 1 - _TC"
	
	pr.append("items", {
		"item_code": args.item or args.item_code or "_Test Item",
		"warehouse": args.warehouse or "_Test Warehouse - _TC",
		"qty": args.qty or 5,
		"received_qty": args.qty or 5,
		"rate": args.rate or 50,
		"conversion_factor": 1.0,
		"serial_no": args.serial_no
	})
	if not args.do_not_save:
		pr.insert()
		if not args.do_not_submit:
			pr.submit()
	return pr


test_dependencies = ["BOM", "Item Price"]
test_records = frappe.get_test_records('Purchase Receipt')
