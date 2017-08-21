# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import frappe, erpnext
import frappe.defaults
from frappe.utils import cint, flt, cstr, today, random_string
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice
from erpnext import set_perpetual_inventory
from erpnext.stock.doctype.serial_no.serial_no import SerialNoDuplicateError
from erpnext.accounts.doctype.account.test_account import get_inventory_account

class TestPurchaseReceipt(unittest.TestCase):
	def setUp(self):
		frappe.db.set_value("Buying Settings", None, "allow_multiple_items", 1)

	def test_make_purchase_invoice(self):
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
		company = frappe.db.get_value('Warehouse', '_Test Warehouse - _TC', 'company')
		set_perpetual_inventory(0, company)

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
		pr = frappe.copy_doc(test_records[0])
		set_perpetual_inventory(1, pr.company)
		self.assertEqual(cint(erpnext.is_perpetual_inventory_enabled(pr.company)), 1)
		pr.insert()
		pr.submit()

		gl_entries = get_gl_entries("Purchase Receipt", pr.name)

		self.assertTrue(gl_entries)

		stock_in_hand_account = get_inventory_account(pr.company, pr.get("items")[0].warehouse)
		fixed_asset_account = get_inventory_account(pr.company, pr.get("items")[1].warehouse)

		if stock_in_hand_account == fixed_asset_account:
			expected_values = {
				stock_in_hand_account: [750.0, 0.0],
				"Stock Received But Not Billed - _TC": [0.0, 500.0],
				"Expenses Included In Valuation - _TC": [0.0, 250.0]
			}
		else:
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

		set_perpetual_inventory(0, pr.company)

	def test_subcontracting(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		make_stock_entry(item_code="_Test Item", target="_Test Warehouse 1 - _TC", qty=100, basic_rate=100)
		make_stock_entry(item_code="_Test Item Home Desktop 100", target="_Test Warehouse 1 - _TC",
			qty=100, basic_rate=100)

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

	def test_purchase_return(self):
		set_perpetual_inventory()

		pr = make_purchase_receipt()

		return_pr = make_purchase_receipt(is_return=1, return_against=pr.name, qty=-2)

		# check sle
		outgoing_rate = frappe.db.get_value("Stock Ledger Entry", {"voucher_type": "Purchase Receipt",
			"voucher_no": return_pr.name}, "outgoing_rate")

		self.assertEqual(outgoing_rate, 50)


		# check gl entries for return
		gl_entries = get_gl_entries("Purchase Receipt", return_pr.name)

		self.assertTrue(gl_entries)
		stock_in_hand_account = get_inventory_account(return_pr.company)

		expected_values = {
			stock_in_hand_account: [0.0, 100.0],
			"Stock Received But Not Billed - _TC": [100.0, 0.0],
		}

		for gle in gl_entries:
			self.assertEquals(expected_values[gle.account][0], gle.debit)
			self.assertEquals(expected_values[gle.account][1], gle.credit)

		set_perpetual_inventory(0)

	def test_purchase_return_for_rejected_qty(self):
		set_perpetual_inventory()

		pr = make_purchase_receipt(received_qty=4, qty=2)

		return_pr = make_purchase_receipt(is_return=1, return_against=pr.name, received_qty = -4, qty=-2)

		actual_qty = frappe.db.get_value("Stock Ledger Entry", {"voucher_type": "Purchase Receipt",
			"voucher_no": return_pr.name, 'warehouse': return_pr.items[0].rejected_warehouse}, "actual_qty")

		self.assertEqual(actual_qty, -2)

		set_perpetual_inventory(0)

	def test_purchase_return_for_serialized_items(self):
		def _check_serial_no_values(serial_no, field_values):
			serial_no = frappe.get_doc("Serial No", serial_no)
			for field, value in field_values.items():
				self.assertEquals(cstr(serial_no.get(field)), value)

		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		pr = make_purchase_receipt(item_code="_Test Serialized Item With Series", qty=1)

		serial_no = get_serial_nos(pr.get("items")[0].serial_no)[0]

		_check_serial_no_values(serial_no, {
			"warehouse": "_Test Warehouse - _TC",
			"purchase_document_no": pr.name
		})

		return_pr = make_purchase_receipt(item_code="_Test Serialized Item With Series", qty=-1,
			is_return=1, return_against=pr.name, serial_no=serial_no)

		_check_serial_no_values(serial_no, {
			"warehouse": "",
			"purchase_document_no": pr.name,
			"delivery_document_no": return_pr.name
		})

	def test_closed_purchase_receipt(self):
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import update_purchase_receipt_status

		pr = make_purchase_receipt(do_not_submit=True)
		pr.submit()

		update_purchase_receipt_status(pr.name, "Closed")
		self.assertEquals(frappe.db.get_value("Purchase Receipt", pr.name, "status"), "Closed")

	def test_pr_billing_status(self):
		# PO -> PR1 -> PI and PO -> PI and PO -> PR2
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
		from erpnext.buying.doctype.purchase_order.purchase_order \
			import make_purchase_receipt, make_purchase_invoice as make_purchase_invoice_from_po

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

		self.assertEqual(pr2.get("items")[0].billed_amt, 2000)
		self.assertEqual(pr2.per_billed, 80)
		self.assertEqual(pr2.status, "To Bill")

	def test_not_accept_duplicate_serial_no(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

		item_code = frappe.db.get_value('Item', {'has_serial_no': 1})
		if not item_code:
			item = make_item("Test Serial Item 1", dict(has_serial_no = 1))
			item_code = item.name

		serial_no = random_string(5)
		make_purchase_receipt(item_code=item_code, qty=1, serial_no=serial_no)
		create_delivery_note(item_code=item_code, qty=1, serial_no=serial_no)

		pr = make_purchase_receipt(item_code=item_code, qty=1, serial_no=serial_no, do_not_submit=True)
		self.assertRaises(SerialNoDuplicateError, pr.submit)

		se = make_stock_entry(item_code=item_code, target="_Test Warehouse - _TC", qty=1,
			serial_no=serial_no, basic_rate=100, do_not_submit=True)
		self.assertRaises(SerialNoDuplicateError, se.submit)

def get_gl_entries(voucher_type, voucher_no):
	return frappe.db.sql("""select account, debit, credit
		from `tabGL Entry` where voucher_type=%s and voucher_no=%s
		order by account desc""", (voucher_type, voucher_no), as_dict=1)

def make_purchase_receipt(**args):
	frappe.db.set_value("Buying Settings", None, "allow_multiple_items", 1)
	pr = frappe.new_doc("Purchase Receipt")
	args = frappe._dict(args)
	pr.posting_date = args.posting_date or today()
	if args.posting_time:
		pr.posting_time = args.posting_time
	pr.company = args.company or "_Test Company"
	pr.supplier = args.supplier or "_Test Supplier"
	pr.is_subcontracted = args.is_subcontracted or "No"
	pr.supplier_warehouse = "_Test Warehouse 1 - _TC"
	pr.currency = args.currency or "INR"
	pr.is_return = args.is_return
	pr.return_against = args.return_against
	qty = args.qty or 5
	received_qty = args.received_qty or qty
	rejected_qty = args.rejected_qty or flt(received_qty) - flt(qty)

	pr.append("items", {
		"item_code": args.item or args.item_code or "_Test Item",
		"warehouse": args.warehouse or "_Test Warehouse - _TC",
		"qty": qty,
		"received_qty": received_qty,
		"rejected_qty": rejected_qty,
		"rejected_warehouse": args.rejected_warehouse or "_Test Rejected Warehouse - _TC" if rejected_qty != 0 else "",
		"rate": args.rate or 50,
		"conversion_factor": 1.0,
		"serial_no": args.serial_no,
		"stock_uom": "_Test UOM"
	})

	if not args.do_not_save:
		pr.insert()
		if not args.do_not_submit:
			pr.submit()
	return pr


test_dependencies = ["BOM", "Item Price"]
test_records = frappe.get_test_records('Purchase Receipt')
