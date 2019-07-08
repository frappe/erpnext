# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import flt
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice


def get_adjustment_entry():
	ae = frappe.new_doc("Adjustment Entry")
	ae.company = "_Test Company"
	ae.payment_currency = "INR"
	ae.customer = "_Test Customer"
	ae.supplier = "_Test Supplier"
	ae.set_party_account_details("Customer", ae.customer)
	ae.set_party_account_details("Supplier", ae.supplier)
	ae.get_unreconciled_entries()
	return ae


def get_gle(voucher_no):
	return frappe.db.sql("""select account, debit, credit, against_voucher
		from `tabGL Entry` where voucher_type='Adjustment Entry' and voucher_no=%s
		order by account asc""", voucher_no, as_dict=1)

class TestAdjustmentEntry(unittest.TestCase):
	def test_adjustment_entry_allocate_payment_amount(self):
		sales_invoice = create_sales_invoice(rate=300, qty=1)
		purchase_invoice = make_purchase_invoice(rate=300, qty=1)
		ae = get_adjustment_entry()
		ae.debit_entries = [ent for ent in ae.debit_entries if ent.voucher_number == sales_invoice.name]
		ae.credit_entries = [ent for ent in ae.credit_entries if ent.voucher_number == purchase_invoice.name]
		ae.allocate_payment_amount = True
		ae.allocate_amount_to_references()
		ae.insert()
		self.assertEqual(ae.receivable_adjusted, ae.payable_adjusted)
		self.assertEqual(ae.difference_amount, 0)

	def test_adjustment_entry_positive_outstanding_gl_entries(self):
		sales_invoice = create_sales_invoice(rate=300, qty=1)
		purchase_invoice = make_purchase_invoice(rate=300, qty=1)
		ae = get_adjustment_entry()
		ae.debit_entries = [ent for ent in ae.debit_entries if ent.voucher_number == sales_invoice.name]
		ae.credit_entries = [ent for ent in ae.credit_entries if ent.voucher_number == purchase_invoice.name]
		ae.allocate_payment_amount = True
		ae.allocate_amount_to_references()
		ae.insert()
		ae.submit()
		expected_gle = dict((d[0], d) for d in [
			["Debtors - _TC", 0, 300, sales_invoice.name],
			["Creditors - _TC", 300, 0, purchase_invoice.name]
		])
		self.validate_gl_entries(ae.name, expected_gle)
		sales_outstanding_amount = flt(frappe.db.get_value("Sales Invoice", sales_invoice.name, "outstanding_amount"))
		purchase_outstanding_amount = flt(frappe.db.get_value("Purchase Invoice", purchase_invoice.name, "outstanding_amount"))
		self.assertEqual(sales_outstanding_amount, 0)
		self.assertEqual(purchase_outstanding_amount, 0)

	def test_adjustment_entry_negative_outstanding_gl_entries(self):
		credit_note = create_sales_invoice(rate=300, qty=-1, is_return=1)
		debit_note = make_purchase_invoice(rate=300, qty=-1, is_return=1)
		ae = get_adjustment_entry()
		ae.debit_entries = [ent for ent in ae.debit_entries if ent.voucher_number == debit_note.name]
		ae.credit_entries = [ent for ent in ae.credit_entries if ent.voucher_number == credit_note.name]
		ae.allocate_payment_amount = True
		ae.allocate_amount_to_references()
		ae.insert()
		ae.submit()
		expected_gle = dict((d[0], d) for d in [
			["Debtors - _TC", 300, 0, credit_note.name],
			["Creditors - _TC", 0, 300, debit_note.name]
		])
		self.validate_gl_entries(ae.name, expected_gle)
		credit_note_outstanding_amount = flt(
			frappe.db.get_value("Sales Invoice", credit_note.name, "outstanding_amount"))
		debit_note_outstanding_amount = flt(
			frappe.db.get_value("Purchase Invoice", debit_note.name, "outstanding_amount"))
		self.assertEqual(credit_note_outstanding_amount, 0)
		self.assertEqual(debit_note_outstanding_amount, 0)

	def test_adjustment_entry_exchange_gain_loss(self):
		usd_sales_invoice = create_sales_invoice(rate=100, qty=1, currency="USD", conversion_rate=70)
		eur_purchase_invoice = make_purchase_invoice(rate=80, qty=1, currency="EUR", conversion_rate=80)
		ae = get_adjustment_entry()
		ae.debit_entries = [ent for ent in ae.debit_entries if ent.voucher_number == usd_sales_invoice.name]
		ae.credit_entries = [ent for ent in ae.credit_entries if ent.voucher_number == eur_purchase_invoice.name]
		for exchg_rate in ae.exchange_rates:
			if exchg_rate.currency == "USD":
				exchg_rate.exchange_rate_to_base_currency = 71
				exchg_rate.exchange_rate_to_payment_currency = 71
			elif exchg_rate.currency == "EUR":
				exchg_rate.exchange_rate_to_base_currency = 79
				exchg_rate.exchange_rate_to_payment_currency = 79
		ae.recalculate_references(['debit_entries', 'credit_entries'])
		ae.allocate_payment_amount = True
		ae.allocate_amount_to_references()
		ae.insert()
		ae.submit()
		expected_gle = dict((d[0], d) for d in [
			["Debtors - _TC", 0, 6230.99, usd_sales_invoice.name],
			["Creditors - _TC", 6400, 0, eur_purchase_invoice.name],
			["_Test Exchange Gain/Loss - _TC", 0, 169.01, None]
		])
		self.validate_gl_entries(ae.name, expected_gle)
		sales_outstanding_amount = flt(frappe.db.get_value("Sales Invoice", usd_sales_invoice.name, "outstanding_amount"))
		purchase_outstanding_amount = flt(
			frappe.db.get_value("Purchase Invoice", eur_purchase_invoice.name, "outstanding_amount"))
		self.assertEqual(sales_outstanding_amount, 769.014085)
		self.assertEqual(purchase_outstanding_amount, 0)

	def validate_gl_entries(self, voucher_no, expected_gle):
		gl_entries = get_gle(voucher_no)
		self.assertTrue(gl_entries)
		self.assertEqual(len(expected_gle), len(gl_entries))
		for gle in gl_entries:
			self.assertEqual(expected_gle[gle.account][0], gle.account)
			self.assertEqual(expected_gle[gle.account][1], gle.debit)
			self.assertEqual(expected_gle[gle.account][2], gle.credit)
			self.assertEqual(expected_gle[gle.account][3], gle.against_voucher)
