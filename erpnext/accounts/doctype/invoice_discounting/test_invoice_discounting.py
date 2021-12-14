# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe
from frappe.utils import add_days, flt, nowdate

from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.accounts.doctype.journal_entry.journal_entry import get_payment_entry_against_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import get_gl_entries


class TestInvoiceDiscounting(unittest.TestCase):
	def setUp(self):
		self.ar_credit = create_account(account_name="_Test Accounts Receivable Credit", parent_account = "Accounts Receivable - _TC", company="_Test Company")
		self.ar_discounted = create_account(account_name="_Test Accounts Receivable Discounted", parent_account = "Accounts Receivable - _TC", company="_Test Company")
		self.ar_unpaid = create_account(account_name="_Test Accounts Receivable Unpaid", parent_account = "Accounts Receivable - _TC", company="_Test Company")
		self.short_term_loan = create_account(account_name="_Test Short Term Loan", parent_account = "Source of Funds (Liabilities) - _TC", company="_Test Company")
		self.bank_account = create_account(account_name="_Test Bank 2", parent_account = "Bank Accounts - _TC", company="_Test Company")
		self.bank_charges_account = create_account(account_name="_Test Bank Charges Account", parent_account = "Expenses - _TC", company="_Test Company")
		frappe.db.set_value("Company", "_Test Company", "default_bank_account", self.bank_account)

	def test_total_amount(self):
		inv1 = create_sales_invoice(rate=200)
		inv2 = create_sales_invoice(rate=500)

		inv_disc = create_invoice_discounting([inv1.name, inv2.name],
			do_not_submit=True,
			accounts_receivable_credit=self.ar_credit,
			accounts_receivable_discounted=self.ar_discounted,
			accounts_receivable_unpaid=self.ar_unpaid,
			short_term_loan=self.short_term_loan,
			bank_charges_account=self.bank_charges_account,
			bank_account=self.bank_account
			)
		self.assertEqual(inv_disc.total_amount, 700)

	def test_gl_entries_in_base_currency(self):
		inv = create_sales_invoice(rate=200)
		inv_disc = create_invoice_discounting([inv.name],
			accounts_receivable_credit=self.ar_credit,
			accounts_receivable_discounted=self.ar_discounted,
			accounts_receivable_unpaid=self.ar_unpaid,
			short_term_loan=self.short_term_loan,
			bank_charges_account=self.bank_charges_account,
			bank_account=self.bank_account
			)

		gle = get_gl_entries("Invoice Discounting", inv_disc.name)

		expected_gle = {
			inv.debit_to: [0.0, 200],
			self.ar_credit: [200, 0.0]
		}
		for i, gle in enumerate(gle):
			self.assertEqual([gle.debit, gle.credit], expected_gle.get(gle.account))

	def test_loan_on_submit(self):
		inv = create_sales_invoice(rate=300)
		inv_disc = create_invoice_discounting([inv.name],
			accounts_receivable_credit=self.ar_credit,
			accounts_receivable_discounted=self.ar_discounted,
			accounts_receivable_unpaid=self.ar_unpaid,
			short_term_loan=self.short_term_loan,
			bank_charges_account=self.bank_charges_account,
			bank_account=self.bank_account,
			start=nowdate(),
			period=60
			)
		self.assertEqual(inv_disc.status, "Sanctioned")
		self.assertEqual(inv_disc.loan_end_date, add_days(inv_disc.loan_start_date, inv_disc.loan_period))


	def test_on_disbursed(self):
		inv = create_sales_invoice(rate=500)
		inv_disc = create_invoice_discounting([inv.name],
			accounts_receivable_credit=self.ar_credit,
			accounts_receivable_discounted=self.ar_discounted,
			accounts_receivable_unpaid=self.ar_unpaid,
			short_term_loan=self.short_term_loan,
			bank_charges_account=self.bank_charges_account,
			bank_account=self.bank_account,
			bank_charges=100
			)

		je = inv_disc.create_disbursement_entry()

		self.assertEqual(je.accounts[0].account, self.bank_account)
		self.assertEqual(je.accounts[0].debit_in_account_currency, flt(inv_disc.total_amount) - flt(inv_disc.bank_charges))

		self.assertEqual(je.accounts[1].account, self.bank_charges_account)
		self.assertEqual(je.accounts[1].debit_in_account_currency, flt(inv_disc.bank_charges))

		self.assertEqual(je.accounts[2].account, self.short_term_loan)
		self.assertEqual(je.accounts[2].credit_in_account_currency, flt(inv_disc.total_amount))

		self.assertEqual(je.accounts[3].account, self.ar_discounted)
		self.assertEqual(je.accounts[3].debit_in_account_currency, flt(inv.outstanding_amount))

		self.assertEqual(je.accounts[4].account, self.ar_credit)
		self.assertEqual(je.accounts[4].credit_in_account_currency, flt(inv.outstanding_amount))


		je.posting_date = nowdate()
		je.submit()

		inv_disc.reload()
		self.assertEqual(inv_disc.status, "Disbursed")

		inv.reload()
		self.assertEqual(inv.outstanding_amount, 500)

	def test_on_close_after_loan_period(self):
		inv = create_sales_invoice(rate=600)
		inv_disc = create_invoice_discounting([inv.name],
			accounts_receivable_credit=self.ar_credit,
			accounts_receivable_discounted=self.ar_discounted,
			accounts_receivable_unpaid=self.ar_unpaid,
			short_term_loan=self.short_term_loan,
			bank_charges_account=self.bank_charges_account,
			bank_account=self.bank_account,
			start=nowdate(),
			period=60
			)

		je1 = inv_disc.create_disbursement_entry()
		je1.posting_date = nowdate()
		je1.submit()

		je2 = inv_disc.close_loan()

		self.assertEqual(je2.accounts[0].account, self.short_term_loan)
		self.assertEqual(je2.accounts[0].debit_in_account_currency, flt(inv_disc.total_amount))

		self.assertEqual(je2.accounts[1].account, self.bank_account)
		self.assertEqual(je2.accounts[1].credit_in_account_currency, flt(inv_disc.total_amount))

		self.assertEqual(je2.accounts[2].account, self.ar_discounted)
		self.assertEqual(je2.accounts[2].credit_in_account_currency, flt(inv.outstanding_amount))

		self.assertEqual(je2.accounts[3].account, self.ar_unpaid)
		self.assertEqual(je2.accounts[3].debit_in_account_currency, flt(inv.outstanding_amount))

		je2.posting_date = nowdate()
		je2.submit()
		inv_disc.reload()

		self.assertEqual(inv_disc.status, "Settled")

	def test_on_close_after_loan_period_after_inv_payment(self):
		inv = create_sales_invoice(rate=600)
		inv_disc = create_invoice_discounting([inv.name],
			accounts_receivable_credit=self.ar_credit,
			accounts_receivable_discounted=self.ar_discounted,
			accounts_receivable_unpaid=self.ar_unpaid,
			short_term_loan=self.short_term_loan,
			bank_charges_account=self.bank_charges_account,
			bank_account=self.bank_account,
			start=nowdate(),
			period=60
			)

		je1 = inv_disc.create_disbursement_entry()
		je1.posting_date = nowdate()
		je1.submit()

		je_on_payment = frappe.get_doc(get_payment_entry_against_invoice("Sales Invoice", inv.name))
		je_on_payment.posting_date = nowdate()
		je_on_payment.cheque_no = "126981"
		je_on_payment.cheque_date = nowdate()
		je_on_payment.save()
		je_on_payment.submit()

		je2 = inv_disc.close_loan()

		self.assertEqual(je2.accounts[0].account, self.short_term_loan)
		self.assertEqual(je2.accounts[0].debit_in_account_currency, flt(inv_disc.total_amount))

		self.assertEqual(je2.accounts[1].account, self.bank_account)
		self.assertEqual(je2.accounts[1].credit_in_account_currency, flt(inv_disc.total_amount))

	def test_on_close_before_loan_period(self):
		inv = create_sales_invoice(rate=700)
		inv_disc = create_invoice_discounting([inv.name],
			accounts_receivable_credit=self.ar_credit,
			accounts_receivable_discounted=self.ar_discounted,
			accounts_receivable_unpaid=self.ar_unpaid,
			short_term_loan=self.short_term_loan,
			bank_charges_account=self.bank_charges_account,
			bank_account=self.bank_account,
			start=add_days(nowdate(), -80),
			period=60
		)

		je1 = inv_disc.create_disbursement_entry()
		je1.posting_date = nowdate()
		je1.submit()

		je2 = inv_disc.close_loan()
		je2.posting_date = nowdate()
		je2.submit()

		self.assertEqual(je2.accounts[0].account, self.short_term_loan)
		self.assertEqual(je2.accounts[0].debit_in_account_currency, flt(inv_disc.total_amount))

		self.assertEqual(je2.accounts[1].account, self.bank_account)
		self.assertEqual(je2.accounts[1].credit_in_account_currency, flt(inv_disc.total_amount))

	def test_make_payment_before_loan_period(self):
		#it has problem
		inv = create_sales_invoice(rate=700)
		inv_disc = create_invoice_discounting([inv.name],
				accounts_receivable_credit=self.ar_credit,
				accounts_receivable_discounted=self.ar_discounted,
				accounts_receivable_unpaid=self.ar_unpaid,
				short_term_loan=self.short_term_loan,
				bank_charges_account=self.bank_charges_account,
				bank_account=self.bank_account
				)
		je = inv_disc.create_disbursement_entry()
		inv_disc.reload()
		je.posting_date = nowdate()
		je.submit()

		je_on_payment = frappe.get_doc(get_payment_entry_against_invoice("Sales Invoice", inv.name))
		je_on_payment.posting_date = nowdate()
		je_on_payment.cheque_no = "126981"
		je_on_payment.cheque_date = nowdate()
		je_on_payment.save()
		je_on_payment.submit()

		self.assertEqual(je_on_payment.accounts[0].account, self.ar_discounted)
		self.assertEqual(je_on_payment.accounts[0].credit_in_account_currency, flt(inv.outstanding_amount))
		self.assertEqual(je_on_payment.accounts[1].account, self.bank_account)
		self.assertEqual(je_on_payment.accounts[1].debit_in_account_currency, flt(inv.outstanding_amount))

		inv.reload()
		self.assertEqual(inv.outstanding_amount, 0)

	def test_make_payment_before_after_period(self):
		#it has problem
		inv = create_sales_invoice(rate=700)
		inv_disc = create_invoice_discounting([inv.name],
				accounts_receivable_credit=self.ar_credit,
				accounts_receivable_discounted=self.ar_discounted,
				accounts_receivable_unpaid=self.ar_unpaid,
				short_term_loan=self.short_term_loan,
				bank_charges_account=self.bank_charges_account,
				bank_account=self.bank_account,
				loan_start_date=add_days(nowdate(), -10),
				period=5
				)
		je = inv_disc.create_disbursement_entry()
		inv_disc.reload()
		je.posting_date = nowdate()
		je.submit()

		je = inv_disc.close_loan()
		inv_disc.reload()
		je.posting_date = nowdate()
		je.submit()

		je_on_payment = frappe.get_doc(get_payment_entry_against_invoice("Sales Invoice", inv.name))
		je_on_payment.posting_date = nowdate()
		je_on_payment.cheque_no = "126981"
		je_on_payment.cheque_date = nowdate()
		je_on_payment.submit()

		self.assertEqual(je_on_payment.accounts[0].account, self.ar_unpaid)
		self.assertEqual(je_on_payment.accounts[0].credit_in_account_currency, flt(inv.outstanding_amount))
		self.assertEqual(je_on_payment.accounts[1].account, self.bank_account)
		self.assertEqual(je_on_payment.accounts[1].debit_in_account_currency, flt(inv.outstanding_amount))

		inv.reload()
		self.assertEqual(inv.outstanding_amount, 0)


def create_invoice_discounting(invoices, **args):
	args = frappe._dict(args)
	inv_disc = frappe.new_doc("Invoice Discounting")
	inv_disc.posting_date = args.posting_date or nowdate()
	inv_disc.company = args.company or "_Test Company"
	inv_disc.bank_account = args.bank_account
	inv_disc.short_term_loan = args.short_term_loan
	inv_disc.accounts_receivable_credit = args.accounts_receivable_credit
	inv_disc.accounts_receivable_discounted = args.accounts_receivable_discounted
	inv_disc.accounts_receivable_unpaid = args.accounts_receivable_unpaid
	inv_disc.short_term_loan=args.short_term_loan
	inv_disc.bank_charges_account=args.bank_charges_account
	inv_disc.bank_account=args.bank_account
	inv_disc.loan_start_date = args.start or nowdate()
	inv_disc.loan_period = args.period or 30
	inv_disc.bank_charges = flt(args.bank_charges)

	for d in invoices:
		inv_disc.append("invoices", {
			"sales_invoice": d
		})
	inv_disc.insert()

	if not args.do_not_submit:
		inv_disc.submit()

	return inv_disc
