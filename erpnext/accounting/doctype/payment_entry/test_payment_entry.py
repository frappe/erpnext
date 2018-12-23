# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import flt, nowdate
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.accounting.doctype.payment_entry.payment_entry import get_payment_entry, InvalidPaymentEntry
from erpnext.accounting.doctype.sales_invoice.test_sales_invoice import create_sales_invoice, create_sales_invoice_against_cost_center
from erpnext.accounting.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice, make_purchase_invoice_against_cost_center
from erpnext.hr.doctype.expense_claim.test_expense_claim import make_expense_claim

test_dependencies = ["Item"]


class TestPaymentEntry(unittest.TestCase):
	def test_payment_entry_against_order(self):
		so = make_sales_order()
		pe = get_payment_entry("Sales Order", so.name, bank_account="_Test Cash - _TC")
		pe.paid_from = "Debtors - _TC"
		pe.insert()
		pe.submit()

		expected_gle = dict((d[0], d) for d in [
			["Debtors - _TC", 0, 1000, so.name],
			["_Test Cash - _TC", 1000.0, 0, None]
		])

		self.validate_gl_entries(pe.name, expected_gle)

		so_advance_paid = frappe.db.get_value("Sales Order", so.name, "advance_paid")
		self.assertEqual(so_advance_paid, 1000)

		pe.cancel()

		self.assertFalse(self.get_gle(pe.name))

		so_advance_paid = frappe.db.get_value("Sales Order", so.name, "advance_paid")
		self.assertEqual(so_advance_paid, 0)

	def test_payment_entry_for_blocked_supplier_invoice(self):
		supplier = frappe.get_doc('Supplier', '_Test Supplier')
		supplier.on_hold = 1
		supplier.hold_type = 'Invoices'
		supplier.save()

		self.assertRaises(frappe.ValidationError, make_purchase_invoice)

		supplier.on_hold = 0
		supplier.save()

	def test_payment_entry_for_blocked_supplier_payments(self):
		supplier = frappe.get_doc('Supplier', '_Test Supplier')
		supplier.on_hold = 1
		supplier.hold_type = 'Payments'
		supplier.save()

		pi = make_purchase_invoice()

		self.assertRaises(
			frappe.ValidationError, get_payment_entry, dt='Purchase Invoice', dn=pi.name,
			bank_account="_Test Bank - _TC")

		supplier.on_hold = 0
		supplier.save()

	def test_payment_entry_for_blocked_supplier_payments_today_date(self):
		supplier = frappe.get_doc('Supplier', '_Test Supplier')
		supplier.on_hold = 1
		supplier.hold_type = 'Payments'
		supplier.release_date = nowdate()
		supplier.save()

		pi = make_purchase_invoice()

		self.assertRaises(
			frappe.ValidationError, get_payment_entry, dt='Purchase Invoice', dn=pi.name,
			bank_account="_Test Bank - _TC")

		supplier.on_hold = 0
		supplier.save()

	def test_payment_entry_for_blocked_supplier_payments_past_date(self):
		# this test is meant to fail only if something fails in the try block
		with self.assertRaises(Exception):
			try:
				supplier = frappe.get_doc('Supplier', '_Test Supplier')
				supplier.on_hold = 1
				supplier.hold_type = 'Payments'
				supplier.release_date = '2018-03-01'
				supplier.save()

				pi = make_purchase_invoice()

				get_payment_entry('Purchase Invoice', pi.name, bank_account="_Test Bank - _TC")

				supplier.on_hold = 0
				supplier.save()
			except:
				pass
			else:
				raise Exception

	def test_payment_entry_against_si_usd_to_usd(self):
		si = create_sales_invoice(customer="_Test Customer USD", debit_to="_Test Receivable USD - _TC",
			currency="USD", conversion_rate=50)
		pe = get_payment_entry("Sales Invoice", si.name, bank_account="_Test Bank USD - _TC")
		pe.reference_no = "1"
		pe.reference_date = "2016-01-01"
		pe.target_exchange_rate = 50
		pe.insert()
		pe.submit()

		expected_gle = dict((d[0], d) for d in [
			["_Test Receivable USD - _TC", 0, 5000, si.name],
			["_Test Bank USD - _TC", 5000.0, 0, None]
		])

		self.validate_gl_entries(pe.name, expected_gle)

		outstanding_amount = flt(frappe.db.get_value("Sales Invoice", si.name, "outstanding_amount"))
		self.assertEqual(outstanding_amount, 0)

		pe.cancel()
		self.assertFalse(self.get_gle(pe.name))

		outstanding_amount = flt(frappe.db.get_value("Sales Invoice", si.name, "outstanding_amount"))
		self.assertEqual(outstanding_amount, 100)

	def test_payment_entry_against_pi(self):
		pi = make_purchase_invoice(supplier="_Test Supplier USD", debit_to="_Test Payable USD - _TC",
			currency="USD", conversion_rate=50)
		pe = get_payment_entry("Purchase Invoice", pi.name, bank_account="_Test Bank USD - _TC")
		pe.reference_no = "1"
		pe.reference_date = "2016-01-01"
		pe.source_exchange_rate = 50
		pe.insert()
		pe.submit()

		expected_gle = dict((d[0], d) for d in [
			["_Test Payable USD - _TC", 12500, 0, pi.name],
			["_Test Bank USD - _TC", 0, 12500, None]
		])

		self.validate_gl_entries(pe.name, expected_gle)

		outstanding_amount = flt(frappe.db.get_value("Sales Invoice", pi.name, "outstanding_amount"))
		self.assertEqual(outstanding_amount, 0)

	def test_payment_entry_against_ec(self):

		payable = frappe.get_cached_value('Company',  "_Test Company",  'default_payable_account')
		ec = make_expense_claim(payable, 300, 300, "_Test Company", "Travel Expenses - _TC")
		pe = get_payment_entry("Expense Claim", ec.name, bank_account="_Test Bank USD - _TC", bank_amount=300)
		pe.reference_no = "1"
		pe.reference_date = "2016-01-01"
		pe.source_exchange_rate = 1
		pe.paid_to = payable
		pe.insert()
		pe.submit()

		expected_gle = dict((d[0], d) for d in [
			[payable, 300, 0, ec.name],
			["_Test Bank USD - _TC", 0, 300, None]
		])

		self.validate_gl_entries(pe.name, expected_gle)

		outstanding_amount = flt(frappe.db.get_value("Expense Claim", ec.name, "total_sanctioned_amount")) - \
			flt(frappe.db.get_value("Expense Claim", ec.name, "total_amount_reimbursed"))
		self.assertEqual(outstanding_amount, 0)

	def test_payment_entry_against_si_usd_to_inr(self):
		si = create_sales_invoice(customer="_Test Customer USD", debit_to="_Test Receivable USD - _TC",
			currency="USD", conversion_rate=50)
		pe = get_payment_entry("Sales Invoice", si.name, party_amount=20,
			bank_account="_Test Bank - _TC", bank_amount=900)
		pe.reference_no = "1"
		pe.reference_date = "2016-01-01"

		self.assertEqual(pe.difference_amount, 100)

		pe.append("deductions", {
			"account": "_Test Exchange Gain/Loss - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"amount": 100
		})
		pe.insert()
		pe.submit()

		expected_gle = dict((d[0], d) for d in [
			["_Test Receivable USD - _TC", 0, 1000, si.name],
			["_Test Bank - _TC", 900, 0, None],
			["_Test Exchange Gain/Loss - _TC", 100.0, 0, None],
		])

		self.validate_gl_entries(pe.name, expected_gle)

		outstanding_amount = flt(frappe.db.get_value("Sales Invoice", si.name, "outstanding_amount"))
		self.assertEqual(outstanding_amount, 80)

	def test_payment_entry_retrieves_last_exchange_rate(self):
		from erpnext.setup.doctype.currency_exchange.test_currency_exchange import test_records, save_new_records

		save_new_records(test_records)

		pe = frappe.new_doc("Payment Entry")
		pe.payment_type = "Pay"
		pe.company = "_Test Company"
		pe.posting_date = "2016-01-10"
		pe.paid_from = "_Test Bank USD - _TC"
		pe.paid_to = "_Test Bank - _TC"
		pe.paid_amount = 100
		pe.received_amount = 100
		pe.reference_no = "3"
		pe.reference_date = "2016-01-10"
		pe.party_type = "Supplier"
		pe.party = "_Test Supplier USD"

		pe.setup_party_account_field()
		pe.set_missing_values()
		pe.set_exchange_rate()
		pe.set_amounts()

		self.assertEqual(
			pe.source_exchange_rate, 65.1,
			"{0} is not equal to {1}".format(pe.source_exchange_rate, 65.1)
		)

	def test_internal_transfer_usd_to_inr(self):
		pe = frappe.new_doc("Payment Entry")
		pe.payment_type = "Internal Transfer"
		pe.company = "_Test Company"
		pe.paid_from = "_Test Bank USD - _TC"
		pe.paid_to = "_Test Bank - _TC"
		pe.paid_amount = 100
		pe.source_exchange_rate = 50
		pe.received_amount = 4500
		pe.reference_no = "2"
		pe.reference_date = nowdate()

		pe.setup_party_account_field()
		pe.set_missing_values()
		pe.set_exchange_rate()
		pe.set_amounts()

		self.assertEqual(pe.difference_amount, 500)

		pe.append("deductions", {
			"account": "_Test Exchange Gain/Loss - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"amount": 500
		})

		pe.insert()
		pe.submit()

		expected_gle = dict((d[0], d) for d in [
			["_Test Bank USD - _TC", 0, 5000, None],
			["_Test Bank - _TC", 4500, 0, None],
			["_Test Exchange Gain/Loss - _TC", 500.0, 0, None],
		])

		self.validate_gl_entries(pe.name, expected_gle)

	def test_payment_against_negative_sales_invoice(self):
		pe1 = frappe.new_doc("Payment Entry")
		pe1.payment_type = "Pay"
		pe1.company = "_Test Company"
		pe1.party_type = "Customer"
		pe1.party = "_Test Customer"
		pe1.paid_from = "_Test Cash - _TC"
		pe1.paid_amount = 100
		pe1.received_amount = 100

		self.assertRaises(InvalidPaymentEntry, pe1.validate)

		si1 = create_sales_invoice()

		# create full payment entry against si1
		pe2 = get_payment_entry("Sales Invoice", si1.name, bank_account="_Test Cash - _TC")
		pe2.insert()
		pe2.submit()

		# create return entry against si1
		create_sales_invoice(is_return=1, return_against=si1.name, qty=-1)
		si1_outstanding = frappe.db.get_value("Sales Invoice", si1.name, "outstanding_amount")
		self.assertEqual(si1_outstanding, -100)

		# pay more than outstanding against si1
		pe3 = get_payment_entry("Sales Invoice", si1.name, bank_account="_Test Cash - _TC")
		pe3.paid_amount = pe3.received_amount = 300
		self.assertRaises(InvalidPaymentEntry, pe3.validate)

		# pay negative outstanding against si1
		pe3.paid_to = "Debtors - _TC"
		pe3.paid_amount = pe3.received_amount = 100

		pe3.insert()
		pe3.submit()

		expected_gle = dict((d[0], d) for d in [
			["Debtors - _TC", 100, 0, si1.name],
			["_Test Cash - _TC", 0, 100, None]
		])

		self.validate_gl_entries(pe3.name, expected_gle)

		outstanding_amount = flt(frappe.db.get_value("Sales Invoice", si1.name, "outstanding_amount"))
		self.assertEqual(outstanding_amount, 0)

		pe3.cancel()
		self.assertFalse(self.get_gle(pe3.name))

		outstanding_amount = flt(frappe.db.get_value("Sales Invoice", si1.name, "outstanding_amount"))
		self.assertEqual(outstanding_amount, -100)

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
			from `tabGL Entry` where voucher_type='Payment Entry' and voucher_no=%s
			order by account asc""", voucher_no, as_dict=1)

	def test_payment_entry_write_off_difference(self):
		si =  create_sales_invoice()
		pe = get_payment_entry("Sales Invoice", si.name, bank_account="_Test Cash - _TC")
		pe.reference_no = "1"
		pe.reference_date = "2016-01-01"
		pe.received_amount = pe.paid_amount = 110
		pe.insert()

		self.assertEqual(pe.unallocated_amount, 10)

		pe.received_amount = pe.paid_amount = 95
		pe.append("deductions", {
			"account": "_Test Write Off - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"amount": 5
		})
		pe.save()

		self.assertEqual(pe.unallocated_amount, 0)
		self.assertEqual(pe.difference_amount, 0)

		pe.submit()

		expected_gle = dict((d[0], d) for d in [
			["Debtors - _TC", 0, 100, si.name],
			["_Test Cash - _TC", 95, 0, None],
			["_Test Write Off - _TC", 5, 0, None]
		])

		self.validate_gl_entries(pe.name, expected_gle)

	def test_payment_entry_exchange_gain_loss(self):
		si =  create_sales_invoice(customer="_Test Customer USD", debit_to="_Test Receivable USD - _TC",
			currency="USD", conversion_rate=50)
		pe = get_payment_entry("Sales Invoice", si.name, bank_account="_Test Bank USD - _TC")
		pe.reference_no = "1"
		pe.reference_date = "2016-01-01"
		pe.target_exchange_rate = 55

		pe.append("deductions", {
			"account": "_Test Exchange Gain/Loss - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"amount": -500
		})
		pe.save()

		self.assertEqual(pe.unallocated_amount, 0)
		self.assertEqual(pe.difference_amount, 0)

		pe.submit()

		expected_gle = dict((d[0], d) for d in [
			["_Test Receivable USD - _TC", 0, 5000, si.name],
			["_Test Bank USD - _TC", 5500, 0, None],
			["_Test Exchange Gain/Loss - _TC", 0, 500, None],
		])

		self.validate_gl_entries(pe.name, expected_gle)

		outstanding_amount = flt(frappe.db.get_value("Sales Invoice", si.name, "outstanding_amount"))
		self.assertEqual(outstanding_amount, 0)

	def test_payment_entry_against_sales_invoice_for_enable_allow_cost_center_in_entry_of_bs_account(self):
		from erpnext.accounting.doctype.cost_center.test_cost_center import create_cost_center
		accounts_settings = frappe.get_doc('Accounts Settings', 'Accounts Settings')
		accounts_settings.allow_cost_center_in_entry_of_bs_account = 1
		accounts_settings.save()
		cost_center = "_Test Cost Center for BS Account - _TC"
		create_cost_center(cost_center_name="_Test Cost Center for BS Account", company="_Test Company")

		si =  create_sales_invoice_against_cost_center(cost_center=cost_center, debit_to="Debtors - _TC")

		pe = get_payment_entry("Sales Invoice", si.name, bank_account="_Test Bank - _TC")
		self.assertEqual(pe.cost_center, si.cost_center)

		pe.reference_no = "112211-1"
		pe.reference_date = nowdate()
		pe.paid_to = "_Test Bank - _TC"
		pe.paid_amount = si.grand_total
		pe.insert()
		pe.submit()

		expected_values = {
			"_Test Bank - _TC": {
				"cost_center": cost_center
			},
			"Debtors - _TC": {
				"cost_center": cost_center
			}
		}

		gl_entries = frappe.db.sql("""select account, cost_center, account_currency, debit, credit,
			debit_in_account_currency, credit_in_account_currency
			from `tabGL Entry` where voucher_type='Payment Entry' and voucher_no=%s
			order by account asc""", pe.name, as_dict=1)

		self.assertTrue(gl_entries)

		for gle in gl_entries:
			self.assertEqual(expected_values[gle.account]["cost_center"], gle.cost_center)

		accounts_settings.allow_cost_center_in_entry_of_bs_account = 0
		accounts_settings.save()

	def test_payment_entry_against_sales_invoice_for_disable_allow_cost_center_in_entry_of_bs_account(self):
		accounts_settings = frappe.get_doc('Accounts Settings', 'Accounts Settings')
		accounts_settings.allow_cost_center_in_entry_of_bs_account = 0
		accounts_settings.save()
		si =  create_sales_invoice(debit_to="Debtors - _TC")

		pe = get_payment_entry("Sales Invoice", si.name, bank_account="_Test Bank - _TC")

		pe.reference_no = "112211-2"
		pe.reference_date = nowdate()
		pe.paid_to = "_Test Bank - _TC"
		pe.paid_amount = si.grand_total
		pe.insert()
		pe.submit()

		gl_entries = frappe.db.sql("""select account, cost_center, account_currency, debit, credit,
			debit_in_account_currency, credit_in_account_currency
			from `tabGL Entry` where voucher_type='Payment Entry' and voucher_no=%s
			order by account asc""", pe.name, as_dict=1)

		self.assertTrue(gl_entries)

		for gle in gl_entries:
			self.assertEqual(gle.cost_center, None)

	def test_payment_entry_against_purchase_invoice_for_enable_allow_cost_center_in_entry_of_bs_account(self):
		from erpnext.accounting.doctype.cost_center.test_cost_center import create_cost_center
		accounts_settings = frappe.get_doc('Accounts Settings', 'Accounts Settings')
		accounts_settings.allow_cost_center_in_entry_of_bs_account = 1
		accounts_settings.save()
		cost_center = "_Test Cost Center for BS Account - _TC"
		create_cost_center(cost_center_name="_Test Cost Center for BS Account", company="_Test Company")

		pi =  make_purchase_invoice_against_cost_center(cost_center=cost_center, credit_to="Creditors - _TC")

		pe = get_payment_entry("Purchase Invoice", pi.name, bank_account="_Test Bank - _TC")
		self.assertEqual(pe.cost_center, pi.cost_center)

		pe.reference_no = "112222-1"
		pe.reference_date = nowdate()
		pe.paid_from = "_Test Bank - _TC"
		pe.paid_amount = pi.grand_total
		pe.insert()
		pe.submit()

		expected_values = {
			"_Test Bank - _TC": {
				"cost_center": cost_center
			},
			"Creditors - _TC": {
				"cost_center": cost_center
			}
		}

		gl_entries = frappe.db.sql("""select account, cost_center, account_currency, debit, credit,
			debit_in_account_currency, credit_in_account_currency
			from `tabGL Entry` where voucher_type='Payment Entry' and voucher_no=%s
			order by account asc""", pe.name, as_dict=1)

		self.assertTrue(gl_entries)

		for gle in gl_entries:
			self.assertEqual(expected_values[gle.account]["cost_center"], gle.cost_center)

		accounts_settings.allow_cost_center_in_entry_of_bs_account = 0
		accounts_settings.save()

	def test_payment_entry_against_purchase_invoice_for_disable_allow_cost_center_in_entry_of_bs_account(self):
		accounts_settings = frappe.get_doc('Accounts Settings', 'Accounts Settings')
		accounts_settings.allow_cost_center_in_entry_of_bs_account = 0
		accounts_settings.save()
		pi =  make_purchase_invoice(credit_to="Creditors - _TC")

		pe = get_payment_entry("Purchase Invoice", pi.name, bank_account="_Test Bank - _TC")

		pe.reference_no = "112222-2"
		pe.reference_date = nowdate()
		pe.paid_from = "_Test Bank - _TC"
		pe.paid_amount = pi.grand_total
		pe.insert()
		pe.submit()

		gl_entries = frappe.db.sql("""select account, cost_center, account_currency, debit, credit,
			debit_in_account_currency, credit_in_account_currency
			from `tabGL Entry` where voucher_type='Payment Entry' and voucher_no=%s
			order by account asc""", pe.name, as_dict=1)

		self.assertTrue(gl_entries)

		for gle in gl_entries:
			self.assertEqual(gle.cost_center, None)

	def test_payment_entry_account_and_party_balance_for_enable_allow_cost_center_in_entry_of_bs_account(self):
		from erpnext.accounting.doctype.cost_center.test_cost_center import create_cost_center
		from erpnext.accounting.utils import get_balance_on
		accounts_settings = frappe.get_doc('Accounts Settings', 'Accounts Settings')
		accounts_settings.allow_cost_center_in_entry_of_bs_account = 1
		accounts_settings.save()
		cost_center = "_Test Cost Center for BS Account - _TC"
		create_cost_center(cost_center_name="_Test Cost Center for BS Account", company="_Test Company")

		si =  create_sales_invoice_against_cost_center(cost_center=cost_center, debit_to="Debtors - _TC")

		account_balance = get_balance_on(account="_Test Bank - _TC", cost_center=si.cost_center)
		party_balance = get_balance_on(party_type="Customer", party=si.customer, cost_center=si.cost_center)
		party_account_balance = get_balance_on(si.debit_to, cost_center=si.cost_center)

		pe = get_payment_entry("Sales Invoice", si.name, bank_account="_Test Bank - _TC")
		pe.reference_no = "112211-1"
		pe.reference_date = nowdate()
		pe.paid_to = "_Test Bank - _TC"
		pe.paid_amount = si.grand_total
		pe.insert()
		pe.submit()

		expected_account_balance = account_balance + si.grand_total
		expected_party_balance = party_balance - si.grand_total
		expected_party_account_balance = party_account_balance - si.grand_total

		account_balance = get_balance_on(account=pe.paid_to, cost_center=pe.cost_center)
		party_balance = get_balance_on(party_type="Customer", party=pe.party, cost_center=pe.cost_center)
		party_account_balance = get_balance_on(account=pe.paid_from, cost_center=pe.cost_center)

		self.assertEqual(pe.cost_center, si.cost_center)
		self.assertEqual(expected_account_balance, account_balance)
		self.assertEqual(expected_party_balance, party_balance)
		self.assertEqual(expected_party_account_balance, party_account_balance)

		accounts_settings.allow_cost_center_in_entry_of_bs_account = 0
		accounts_settings.save()
