# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
from frappe.utils import nowdate, add_days
import unittest
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import get_gl_entries
from erpnext.accounts.doctype.account.test_account import create_account

class TestInvoiceDiscounting(unittest.TestCase):
	def setUp(self):
		self.ar_credit = create_account(account_name="_Test Accounts Receivable Credit", parent_account = "Accounts Receivable - _TC")
		self.ar_discounted = create_account(account_name="_Test Accounts Receivable Discounted", parent_account = "Accounts Receivable - _TC")
		self.ar_unpaid = create_account(account_name="_Test Accounts Receivable Unpaid", parent_account = "Accounts Receivable - _TC")
		self.short_term_loan = create_account(account_name="_Test Short Term Loan", parent_account = "Source of Funds (Liabilities) - _TC")
		self.bank_account = create_account(account_name="_Test Bank 2", parent_account = "Bank Accounts - _TC" )
		self.bank_charges_account = create_account(account_name="_Test Bank Charges Account", parent_account = "Expenses - _TC")


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

	'''def test_on_disbursed(self):
		inv = create_sales_invoice(rate=300)
		inv_disc = create_invoice_discounting([inv.name],
			accounts_receivable_credit=self.ar_credit,
			accounts_receivable_discounted=self.ar_discounted,
			accounts_receivable_unpaid=self.ar_unpaid,
			short_term_loan=self.short_term_loan,
			bank_charges_account=self.bank_charges_account,
			bank_account=self.bank_account,
			set_status='Disbursed'
			)

		gle = get_gl_entries("Invoice Discounting", inv_disc.name)
		from pprint import pprint
		pprint(gle)'''

	def test_on_invoice_payment

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

	for d in invoices:
		inv_disc.append("invoices", {
			"sales_invoice": d
		})
	inv_disc.insert()

	if not args.do_not_submit:
		inv_disc.submit()

	if args.set_status:
		inv_disc.status = args.set_status

	return inv_disc
