# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import today
from erpnext.accounts.utils import get_fiscal_year
from erpnext.buying.doctype.supplier.test_supplier import create_supplier

test_dependencies = ["Supplier Group", "Customer Group"]

class TestTaxWithholdingCategory(unittest.TestCase):
	@classmethod
	def setUpClass(self):
		# create relevant supplier, etc
		create_records()
		create_tax_with_holding_category()

	def tearDown(self):
		cancel_invoices()

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
		doc = create_supplier(supplier_name = "Test TDS Supplier ABC",
			tax_withholding_category="Single Threshold TDS")
		supplier = doc.name

		pi = create_purchase_invoice(supplier=supplier)
		pi.submit()
		invoices.append(pi)

		# TDS not applied
		pi = create_purchase_invoice(supplier=supplier, do_not_apply_tds=True)
		pi.submit()
		invoices.append(pi)

		pi = create_purchase_invoice(supplier=supplier)
		pi.submit()
		invoices.append(pi)

		self.assertEqual(pi.taxes_and_charges_deducted, 2000)
		self.assertEqual(pi.grand_total, 8000)

		# delete invoices to avoid clashing
		for d in invoices:
			d.cancel()

	def test_cumulative_threshold_tcs(self):
		frappe.db.set_value("Customer", "Test TCS Customer", "tax_withholding_category", "Cumulative Threshold TCS")
		invoices = []

		# create invoices for lower than single threshold tax rate
		for _ in range(2):
			si = create_sales_invoice(customer = "Test TCS Customer")
			si.submit()
			invoices.append(si)

		# create another invoice whose total when added to previously created invoice,
		# surpasses cumulative threshhold
		si = create_sales_invoice(customer = "Test TCS Customer", rate=12000)
		si.submit()

		# assert tax collection on total invoice amount created until now
		tcs_charged = sum([d.base_tax_amount for d in si.taxes if d.account_head == 'TCS - _TC'])
		self.assertEqual(tcs_charged, 200)
		self.assertEqual(si.grand_total, 12200)
		invoices.append(si)

		# TCS is already collected once, so going forward system will collect TCS on every invoice
		si = create_sales_invoice(customer = "Test TCS Customer", rate=5000)
		si.submit()

		tcs_charged = sum([d.base_tax_amount for d in si.taxes if d.account_head == 'TCS - _TC'])
		self.assertEqual(tcs_charged, 500)
		invoices.append(si)

		#delete invoices to avoid clashing
		for d in invoices:
			d.cancel()

def cancel_invoices():
	purchase_invoices = frappe.get_all("Purchase Invoice", {
		'supplier': ['in', ['Test TDS Supplier', 'Test TDS Supplier1', 'Test TDS Supplier2']],
		'docstatus': 1
	}, pluck="name")

	sales_invoices = frappe.get_all("Sales Invoice", {
		'customer': 'Test TCS Customer',
		'docstatus': 1
	}, pluck="name")

	for d in purchase_invoices:
		frappe.get_doc('Purchase Invoice', d).cancel()
	
	for d in sales_invoices:
		frappe.get_doc('Sales Invoice', d).cancel()

def create_purchase_invoice(**args):
	# return sales invoice doc object
	item = frappe.db.get_value('Item', {'item_name': 'TDS Item'}, "name")

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
			'item_code': item,
			'qty': args.qty or 1,
			'rate': args.rate or 10000,
			'cost_center': 'Main - _TC',
			'expense_account': 'Stock Received But Not Billed - _TC'
		}]
	})

	pi.save()
	return pi

def create_sales_invoice(**args):
	# return sales invoice doc object
	item = frappe.db.get_value('Item', {'item_name': 'TCS Item'}, "name")

	args = frappe._dict(args)
	si = frappe.get_doc({
		"doctype": "Sales Invoice",
		"posting_date": today(),
		"customer": args.customer,
		"company": '_Test Company',
		"taxes_and_charges": "",
		"currency": "INR",
		"debit_to": "Debtors - _TC",
		"taxes": [],
		"items": [{
			'doctype': 'Sales Invoice Item',
			'item_code': item,
			'qty': args.qty or 1,
			'rate': args.rate or 10000,
			'cost_center': 'Main - _TC',
			'expense_account': 'Cost of Goods Sold - _TC'
		}]
	})

	si.save()
	return si

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

	for name in ['Test TCS Customer']:
		if frappe.db.exists('Customer', name):
			continue

		frappe.get_doc({
			"customer_group": "_Test Customer Group",
			"customer_name": name,
			"doctype": "Customer"
		}).insert()

	# create item
	if not frappe.db.exists('Item', "TDS Item"):
		frappe.get_doc({
			"doctype": "Item",
			"item_code": "TDS Item",
			"item_name": "TDS Item",
			"item_group": "All Item Groups",
			"is_stock_item": 0,
		}).insert()

	if not frappe.db.exists('Item', "TCS Item"):
		frappe.get_doc({
			"doctype": "Item",
			"item_code": "TCS Item",
			"item_name": "TCS Item",
			"item_group": "All Item Groups",
			"is_stock_item": 1
		}).insert()

	# create tds account
	if not frappe.db.exists("Account", "TDS - _TC"):
		frappe.get_doc({
			'doctype': 'Account',
			'company': '_Test Company',
			'account_name': 'TDS',
			'parent_account': 'Tax Assets - _TC',
			'report_type': 'Balance Sheet',
			'root_type': 'Asset'
		}).insert()

	# create tcs account
	if not frappe.db.exists("Account", "TCS - _TC"):
		frappe.get_doc({
			'doctype': 'Account',
			'company': '_Test Company',
			'account_name': 'TCS',
			'parent_account': 'Duties and Taxes - _TC',
			'report_type': 'Balance Sheet',
			'root_type': 'Liability'
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

	if not frappe.db.exists("Tax Withholding Category", "Cumulative Threshold TCS"):
		frappe.get_doc({
			"doctype": "Tax Withholding Category",
			"name": "Cumulative Threshold TCS",
			"category_name": "10% TCS",
			"rates": [{
				'fiscal_year': fiscal_year,
				'tax_withholding_rate': 10,
				'single_threshold': 0,
				'cumulative_threshold': 30000.00
			}],
			"accounts": [{
				'company': '_Test Company',
				'account': 'TCS - _TC'
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