# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import flt
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.utils import get_outstanding_invoices, get_negative_outstanding_invoices


def get_adjustment_entry():
	ae = frappe.new_doc("Adjustment Entry")
	ae.company = "_Test Company"
	ae.adjustment_type = "Netting"
	ae.payment_currency = "INR"
	ae.customer = "_Test Customer"
	ae.supplier = "_Test Supplier"
	ae.set_party_account_details("Customer", ae.customer)
	ae.set_party_account_details("Supplier", ae.supplier)
	return ae


class TestAdjustmentEntry(unittest.TestCase):
	def setUp(self):
		self.sales_invoice = create_sales_invoice(rate=300, qty=1)
		self.purchase_invoice = make_purchase_invoice(rate=300, qty=1)

	def test_adjustment_entry_get_unreconciled_entries(self):
		outstanding_sales_invoices = get_outstanding_invoices('Customer', '_Test Customer',
															  'Debtors - _TC') + get_negative_outstanding_invoices(
			'Customer', '_Test Customer', 'Debtors - _TC', 'INR', 'INR')
		outstanding_purchase_invoices = get_outstanding_invoices('Supplier', '_Test Supplier',
																 'Creditors - _TC') + get_negative_outstanding_invoices(
			'Supplier', '_Test Supplier', 'Creditors - _TC', 'INR', 'INR')
		ae = get_adjustment_entry()
		ae.get_unreconciled_entries()
		ae.insert()
		self.assertEqual(len(outstanding_sales_invoices), len(ae.debit_entries))
		self.assertEqual(len(outstanding_purchase_invoices), len(ae.credit_entries))

	def test_adjustment_entry_allocate_payment_amount(self):
		ae = get_adjustment_entry()
		ae.get_unreconciled_entries()
		ae.debit_entries = [ent for ent in ae.debit_entries if ent.voucher_number == self.sales_invoice.name]
		ae.credit_entries = [ent for ent in ae.credit_entries if ent.voucher_number == self.purchase_invoice.name]
		ae.allocate_payment_amount = True
		ae.allocate_amount_to_references()
		ae.insert()
		self.assertEqual(ae.receivable_adjusted, ae.payable_adjusted)
		self.assertEqual(ae.difference_amount, 0)

	def test_adjustment_entry_gl_entries(self):
		ae = get_adjustment_entry()
		ae.get_unreconciled_entries()
		ae.debit_entries = [ent for ent in ae.debit_entries if ent.voucher_number == self.sales_invoice.name]
		ae.credit_entries = [ent for ent in ae.credit_entries if ent.voucher_number == self.purchase_invoice.name]
		ae.allocate_payment_amount = True
		ae.allocate_amount_to_references()
		ae.insert()
		ae.submit()
		expected_gle = dict((d[0], d) for d in [
			["Debtors - _TC", 0, 300, self.sales_invoice.name],
			["Creditors - _TC", 300, 0, self.purchase_invoice.name],
			["_Test Exchange Gain/Loss - _TC", 0 if ae.total_gain_loss > 0 else ae.total_gain_loss, 0 if ae.total_gain_loss <= 0 else ae.total_gain_loss, None]
		])
		self.validate_gl_entries(ae.name, expected_gle)
		sales_outstanding_amount = flt(frappe.db.get_value("Sales Invoice", self.sales_invoice.name, "outstanding_amount"))
		purchase_outstanding_amount = flt(frappe.db.get_value("Purchase Invoice", self.purchase_invoice.name, "outstanding_amount"))
		self.assertEqual(sales_outstanding_amount, 0)
		self.assertEqual(purchase_outstanding_amount, 0)

	def validate_gl_entries(self, voucher_no, expected_gle):
		gl_entries = self.get_gle(voucher_no)

		self.assertTrue(gl_entries)

		for gle in gl_entries:
			self.assertEqual(expected_gle[gle.account][0], gle.account)
			self.assertEqual(expected_gle[gle.account][1], gle.debit)
			self.assertEqual(expected_gle[gle.account][2], gle.credit)
			self.assertEqual(expected_gle[gle.account][3], gle.against_voucher)

	def get_gle(self, voucher_no):
		return frappe.db.sql("""select account, debit, credit, against_voucher
			from `tabGL Entry` where voucher_type='Adjustment Entry' and voucher_no=%s
			order by account asc""", voucher_no, as_dict=1)