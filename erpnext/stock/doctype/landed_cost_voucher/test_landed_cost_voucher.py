# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import frappe
from frappe.utils import flt
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt \
	import set_perpetual_inventory, get_gl_entries, test_records as pr_test_records, make_purchase_receipt
from erpnext.accounting.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounting.doctype.account.test_account import get_inventory_account

class TestLandedCostVoucher(unittest.TestCase):
	def test_landed_cost_voucher(self):
		frappe.db.set_value("Buying Settings", None, "allow_multiple_items", 1)
		set_perpetual_inventory(1)
		pr = frappe.copy_doc(pr_test_records[0])
		pr.submit()

		last_sle = frappe.db.get_value("Stock Ledger Entry", {
				"voucher_type": pr.doctype,
				"voucher_no": pr.name,
				"item_code": "_Test Item",
				"warehouse": "_Test Warehouse - _TC"
			},
			fieldname=["qty_after_transaction", "stock_value"], as_dict=1)

		submit_landed_cost_voucher("Purchase Receipt", pr.name)

		pr_lc_value = frappe.db.get_value("Purchase Receipt Item", {"parent": pr.name}, "landed_cost_voucher_amount")
		self.assertEqual(pr_lc_value, 25.0)

		last_sle_after_landed_cost = frappe.db.get_value("Stock Ledger Entry", {
				"voucher_type": pr.doctype,
				"voucher_no": pr.name,
				"item_code": "_Test Item",
				"warehouse": "_Test Warehouse - _TC"
			},
			fieldname=["qty_after_transaction", "stock_value"], as_dict=1)

		self.assertEqual(last_sle.qty_after_transaction, last_sle_after_landed_cost.qty_after_transaction)

		self.assertEqual(last_sle_after_landed_cost.stock_value - last_sle.stock_value, 25.0)

		gl_entries = get_gl_entries("Purchase Receipt", pr.name)

		self.assertTrue(gl_entries)

		stock_in_hand_account = get_inventory_account(pr.company, pr.get("items")[0].warehouse)
		fixed_asset_account = get_inventory_account(pr.company, pr.get("items")[1].warehouse)

		if stock_in_hand_account == fixed_asset_account:
			expected_values = {
				stock_in_hand_account: [800.0, 0.0],
				"Stock Received But Not Billed - _TC": [0.0, 500.0],
				"Expenses Included In Valuation - _TC": [0.0, 300.0]
			}

		else:
			expected_values = {
				stock_in_hand_account: [400.0, 0.0],
				fixed_asset_account: [400.0, 0.0],
				"Stock Received But Not Billed - _TC": [0.0, 500.0],
				"Expenses Included In Valuation - _TC": [0.0, 300.0]
			}

		for gle in gl_entries:
			self.assertEqual(expected_values[gle.account][0], gle.debit)
			self.assertEqual(expected_values[gle.account][1], gle.credit)

		set_perpetual_inventory(0)

	def test_landed_cost_voucher_against_purchase_invoice(self):
		set_perpetual_inventory(1)

		pi = make_purchase_invoice(update_stock=1, posting_date=frappe.utils.nowdate(),
			posting_time=frappe.utils.nowtime())

		last_sle = frappe.db.get_value("Stock Ledger Entry", {
				"voucher_type": pi.doctype,
				"voucher_no": pi.name,
				"item_code": "_Test Item",
				"warehouse": "_Test Warehouse - _TC"
			},
			fieldname=["qty_after_transaction", "stock_value"], as_dict=1)

		submit_landed_cost_voucher("Purchase Invoice", pi.name)

		pi_lc_value = frappe.db.get_value("Purchase Invoice Item", {"parent": pi.name},
			"landed_cost_voucher_amount")

		self.assertEqual(pi_lc_value, 50.0)

		last_sle_after_landed_cost = frappe.db.get_value("Stock Ledger Entry", {
				"voucher_type": pi.doctype,
				"voucher_no": pi.name,
				"item_code": "_Test Item",
				"warehouse": "_Test Warehouse - _TC"
			},
			fieldname=["qty_after_transaction", "stock_value"], as_dict=1)

		self.assertEqual(last_sle.qty_after_transaction, last_sle_after_landed_cost.qty_after_transaction)

		self.assertEqual(last_sle_after_landed_cost.stock_value - last_sle.stock_value, 50.0)

		gl_entries = get_gl_entries("Purchase Invoice", pi.name)

		self.assertTrue(gl_entries)
		stock_in_hand_account = get_inventory_account(pi.company, pi.get("items")[0].warehouse)

		expected_values = {
			stock_in_hand_account: [300.0, 0.0],
			"Creditors - _TC": [0.0, 250.0],
			"Expenses Included In Valuation - _TC": [0.0, 50.0]
		}

		for gle in gl_entries:
			self.assertEqual(expected_values[gle.account][0], gle.debit)
			self.assertEqual(expected_values[gle.account][1], gle.credit)

		set_perpetual_inventory(0)

	def test_landed_cost_voucher_for_serialized_item(self):
		set_perpetual_inventory(1)
		frappe.db.sql("delete from `tabSerial No` where name in ('SN001', 'SN002', 'SN003', 'SN004', 'SN005')")

		pr = frappe.copy_doc(pr_test_records[0])
		pr.items[0].item_code = "_Test Serialized Item"
		pr.items[0].serial_no = "SN001\nSN002\nSN003\nSN004\nSN005"
		pr.submit()

		serial_no_rate = frappe.db.get_value("Serial No", "SN001", "purchase_rate")

		submit_landed_cost_voucher("Purchase Receipt", pr.name)

		serial_no = frappe.db.get_value("Serial No", "SN001",
			["warehouse", "purchase_rate"], as_dict=1)

		self.assertEqual(serial_no.purchase_rate - serial_no_rate, 5.0)
		self.assertEqual(serial_no.warehouse, "_Test Warehouse - _TC")

		set_perpetual_inventory(0)

	def test_landed_cost_voucher_for_odd_numbers (self):
		set_perpetual_inventory(1)

		pr = make_purchase_receipt(do_not_save=True)
		pr.items[0].cost_center = "_Test Company - _TC"
		for x in range(2):
			pr.append("items", {
				"item_code": "_Test Item",
				"warehouse": "_Test Warehouse - _TC",
				"cost_center": "_Test Company - _TC",
				"qty": 5,
				"rate": 50
			})
		pr.submit()

		lcv = submit_landed_cost_voucher("Purchase Receipt", pr.name, 123.22)

		self.assertEqual(lcv.items[0].applicable_charges, 41.07)
		self.assertEqual(lcv.items[2].applicable_charges, 41.08)

		set_perpetual_inventory(0)

def submit_landed_cost_voucher(receipt_document_type, receipt_document, charges=50):
	ref_doc = frappe.get_doc(receipt_document_type, receipt_document)

	lcv = frappe.new_doc("Landed Cost Voucher")
	lcv.company = "_Test Company"
	lcv.distribute_charges_based_on = 'Amount'

	lcv.set("purchase_receipts", [{
		"receipt_document_type": receipt_document_type,
		"receipt_document": receipt_document,
		"supplier": ref_doc.supplier,
		"posting_date": ref_doc.posting_date,
		"grand_total": ref_doc.base_grand_total
	}])

	lcv.set("taxes", [{
		"description": "Insurance Charges",
		"account": "_Test Account Insurance Charges - _TC",
		"amount": charges
	}])

	lcv.insert()

	distribute_landed_cost_on_items(lcv)

	lcv.submit()

	return lcv

def distribute_landed_cost_on_items(lcv):
	based_on = lcv.distribute_charges_based_on.lower()
	total = sum([flt(d.get(based_on)) for d in lcv.get("items")])

	for item in lcv.get("items"):
		item.applicable_charges = flt(item.get(based_on)) * flt(lcv.total_taxes_and_charges) / flt(total)
		item.applicable_charges = flt(item.applicable_charges, lcv.precision("applicable_charges", item))

test_records = frappe.get_test_records('Landed Cost Voucher')
