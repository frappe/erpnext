# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import today

test_dependencies = ["Supplier Group"]

class TestTaxWithholdingCategory(unittest.TestCase):
	@classmethod
	def setUpClass(self):
		# create relevant supplier, etc
		create_records()

	def test_single_threshold_tds(self):
		frappe.db.set_value("Supplier", "Test TDS Supplier", "tax_withholding_category", "TDS - 194D - Individual")
		pi = create_purchase_invoice()
		pi.submit()

		self.assertEqual(pi.taxes_and_charges_deducted, 800)
		self.assertEqual(pi.grand_total, 15200)

		# check gl entry for the purchase invoice
		gl_entries = frappe.db.get_all('GL Entry', filters={'voucher_no': pi.name}, fields=["*"])
		self.assertEqual(len(gl_entries), 3)
		for d in gl_entries:
			if d.account == pi.credit_to:
				self.assertEqual(d.credit, 15200)
			elif d.account == pi.items[0].get("expense_account"):
				self.assertEqual(d.debit, 16000)
			elif d.account == pi.taxes[0].get("account_head"):
				self.assertEqual(d.credit, 800)
			else:
				raise ValueError("Account head does not match.")

		# delete purchase invoice to avoid it interefering in other tests
		pi.cancel()
		frappe.delete_doc('Purchase Invoice', pi.name)

	def test_cumulative_threshold_tds(self):
		frappe.db.set_value("Supplier", "Test TDS Supplier", "tax_withholding_category", "TDS - 194C - Individual")
		invoices = []

		# create invoices for lower than single threshold tax rate
		for _ in xrange(6):
			pi = create_purchase_invoice()
			pi.submit()
			invoices.append(pi)

		# create another invoice whose total when added to previously created invoice,
		# surpasses cumulative threshhold
		pi = create_purchase_invoice()
		pi.submit()

		# assert equal tax deduction on total invoice amount uptil now
		self.assertEqual(pi.taxes_and_charges_deducted, 1120)
		self.assertEqual(pi.grand_total, 14880)
		invoices.append(pi)

		# delete invoices to avoid clashing
		for d in invoices:
			d.cancel()
			frappe.delete_doc("Purchase Invoice", d.name)

def create_purchase_invoice(qty=1):
	# return sales invoice doc object
	item = frappe.get_doc('Item', {'item_name': 'TDS Item'})
	pi = frappe.get_doc({
		"doctype": "Purchase Invoice",
		"posting_date": today(),
		"apply_tds": 1,
		"supplier": frappe.get_doc('Supplier', {"supplier_name": "Test TDS Supplier"}).name,
		"company": '_Test Company',
		"taxes_and_charges": "",
		"currency": "INR",
		"credit_to": "Creditors - _TC",
		"taxes": [],
		"items": [{
			'doctype': 'Purchase Invoice Item',
			'item_code': item.name,
			'qty': qty,
			'rate': 16000,
			'cost_center': 'Main - _TC',
			'expense_account': 'Stock Received But Not Billed - _TC'
		}]
	})

	pi.save()
	return pi

def create_records():
	# create a new supplier
	frappe.get_doc({
		"supplier_group": "_Test Supplier Group",
		"supplier_name": "Test TDS Supplier",
		"doctype": "Supplier",
		"tax_withholding_category": "TDS - 194D - Individual"
	}).insert()

	# create an item
	frappe.get_doc({
		"doctype": "Item",
		"item_code": "TDS Item",
		"item_name": "TDS Item",
		"item_group": "All Item Groups",
		"company": "_Test Company",
		"is_stock_item": 0,
	}).insert()