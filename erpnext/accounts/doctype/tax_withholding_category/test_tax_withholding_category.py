# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import today
from erpnext.accounts.utils import get_fiscal_year

test_dependencies = ["Supplier Group"]

class TestTaxWithholdingCategory(unittest.TestCase):
	@classmethod
	def setUpClass(self):
		# create relevant supplier, etc
		create_records()
		create_tax_with_holding_category()

	def test_cumulative_threshold_tds(self):
		frappe.db.set_value("Supplier", "Test TDS Supplier", "tax_withholding_category", "Cumulative Threshold TDS")
		invoices = []

		# create invoices for lower than single threshold tax rate
		for _ in range(2):
			pi = create_purchase_invoice(supplier = "Test TDS Supplier")
			pi.submit()
			invoices.append(pi)

		# create another invoice whose total when added to previously created invoice,
		# surpasses cumulative threshhold
		pi = create_purchase_invoice(supplier = "Test TDS Supplier")
		pi.submit()

		# assert equal tax deduction on total invoice amount uptil now
		self.assertEqual(pi.taxes_and_charges_deducted, 3000)
		self.assertEqual(pi.grand_total, 7000)
		invoices.append(pi)

		# TDS is already deducted, so from onward system will deduct the TDS on every invoice
		pi = create_purchase_invoice(supplier = "Test TDS Supplier", rate=5000)
		pi.submit()

		# assert equal tax deduction on total invoice amount uptil now
		self.assertEqual(pi.taxes_and_charges_deducted, 500)
		invoices.append(pi)

		#delete invoices to avoid clashing
		for d in invoices:
			d.cancel()

	def test_single_threshold_tds(self):
		invoices = []
		frappe.db.set_value("Supplier", "Test TDS Supplier1", "tax_withholding_category", "Single Threshold TDS")
		pi = create_purchase_invoice(supplier = "Test TDS Supplier1", rate = 20000)
		pi.submit()
		invoices.append(pi)

		self.assertEqual(pi.taxes_and_charges_deducted, 2000)
		self.assertEqual(pi.grand_total, 18000)

		# check gl entry for the purchase invoice
		gl_entries = frappe.db.get_all('GL Entry', filters={'voucher_no': pi.name}, fields=["*"])
		self.assertEqual(len(gl_entries), 3)
		for d in gl_entries:
			if d.account == pi.credit_to:
				self.assertEqual(d.credit, 18000)
			elif d.account == pi.items[0].get("expense_account"):
				self.assertEqual(d.debit, 20000)
			elif d.account == pi.taxes[0].get("account_head"):
				self.assertEqual(d.credit, 2000)
			else:
				raise ValueError("Account head does not match.")

		pi = create_purchase_invoice(supplier = "Test TDS Supplier1")
		pi.submit()
		invoices.append(pi)

		# TDS amount is 1000 because in previous invoices it's already deducted
		self.assertEqual(pi.taxes_and_charges_deducted, 1000)

		# delete invoices to avoid clashing
		for d in invoices:
			d.cancel()

	def test_single_threshold_tds_with_previous_vouchers(self):
		invoices = []
		frappe.db.set_value("Supplier", "Test TDS Supplier2", "tax_withholding_category", "Single Threshold TDS")
		pi = create_purchase_invoice(supplier="Test TDS Supplier2")
		pi.submit()
		invoices.append(pi)

		pi = create_purchase_invoice(supplier="Test TDS Supplier2")
		pi.submit()
		invoices.append(pi)

		self.assertEqual(pi.taxes_and_charges_deducted, 2000)
		self.assertEqual(pi.grand_total, 8000)

		# delete invoices to avoid clashing
		for d in invoices:
			d.cancel()

	def test_single_threshold_tds_with_previous_vouchers_and_no_tds(self):
		invoices = []
		frappe.db.set_value("Supplier", "Test TDS Supplier2", "tax_withholding_category", "Single Threshold TDS")
		pi = create_purchase_invoice(supplier="Test TDS Supplier2")
		pi.submit()
		invoices.append(pi)

		# TDS not applied
		pi = create_purchase_invoice(supplier="Test TDS Supplier2", do_not_apply_tds=True)
		pi.submit()
		invoices.append(pi)

		pi = create_purchase_invoice(supplier="Test TDS Supplier2")
		pi.submit()
		invoices.append(pi)

		self.assertEqual(pi.taxes_and_charges_deducted, 2000)
		self.assertEqual(pi.grand_total, 8000)

		# delete invoices to avoid clashing
		for d in invoices:
			d.cancel()

def create_purchase_invoice(**args):
	# return sales invoice doc object
	item = frappe.get_doc('Item', {'item_name': 'TDS Item'})

	args = frappe._dict(args)
	pi = frappe.get_doc({
		"doctype": "Purchase Invoice",
		"posting_date": today(),
		"apply_tds": 0 if args.do_not_apply_tds else 1,
		"supplier": args.supplier,
		"company": '_Test Company',
		"taxes_and_charges": "",
		"currency": "INR",
		"credit_to": "Creditors - _TC",
		"taxes": [],
		"items": [{
			'doctype': 'Purchase Invoice Item',
			'item_code': item.name,
			'qty': args.qty or 1,
			'rate': args.rate or 10000,
			'cost_center': 'Main - _TC',
			'expense_account': 'Stock Received But Not Billed - _TC'
		}]
	})

	pi.save()
	return pi

def create_records():
	# create a new suppliers
	for name in ['Test TDS Supplier', 'Test TDS Supplier1', 'Test TDS Supplier2']:
		if frappe.db.exists('Supplier', name):
			continue

		frappe.get_doc({
			"supplier_group": "_Test Supplier Group",
			"supplier_name": name,
			"doctype": "Supplier",
		}).insert()

	# create an item
	if not frappe.db.exists('Item', "TDS Item"):
		frappe.get_doc({
			"doctype": "Item",
			"item_code": "TDS Item",
			"item_name": "TDS Item",
			"item_group": "All Item Groups",
			"is_stock_item": 0,
		}).insert()

	# create an account
	if not frappe.db.exists("Account", "TDS - _TC"):
		frappe.get_doc({
			'doctype': 'Account',
			'company': '_Test Company',
			'account_name': 'TDS',
			'parent_account': 'Tax Assets - _TC',
			'report_type': 'Balance Sheet',
			'root_type': 'Asset'
		}).insert()

def create_tax_with_holding_category():
	fiscal_year = get_fiscal_year(today(), company="_Test Company")[0]

	# Cummulative thresold
	if not frappe.db.exists("Tax Withholding Category", "Cumulative Threshold TDS"):
		frappe.get_doc({
			"doctype": "Tax Withholding Category",
			"name": "Cumulative Threshold TDS",
			"category_name": "10% TDS",
			"rates": [{
				'fiscal_year': fiscal_year,
				'tax_withholding_rate': 10,
				'single_threshold': 0,
				'cumulative_threshold': 30000.00
			}],
			"accounts": [{
				'company': '_Test Company',
				'account': 'TDS - _TC'
			}]
		}).insert()

	# Single thresold
	if not frappe.db.exists("Tax Withholding Category", "Single Threshold TDS"):
		frappe.get_doc({
			"doctype": "Tax Withholding Category",
			"name": "Single Threshold TDS",
			"category_name": "10% TDS",
			"rates": [{
				'fiscal_year': fiscal_year,
				'tax_withholding_rate': 10,
				'single_threshold': 20000.00,
				'cumulative_threshold': 0
			}],
			"accounts": [{
				'company': '_Test Company',
				'account': 'TDS - _TC'
			}]
		}).insert()