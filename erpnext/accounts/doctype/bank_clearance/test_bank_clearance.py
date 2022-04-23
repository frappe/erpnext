# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import add_months, getdate

from erpnext.accounts.doctype.payment_entry.test_payment_entry import get_payment_entry
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.loan_management.doctype.loan.test_loan import (
	create_loan,
	create_loan_accounts,
	create_loan_type,
	create_repayment_entry,
	make_loan_disbursement_entry,
)


class TestBankClearance(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		make_bank_account()
		create_loan_accounts()
		create_loan_masters()
		add_transactions()

	@classmethod
	def tearDownClass(cls):
		frappe.db.set_single_value("Accounts Settings", "delete_linked_ledger_entries", 1)

		payment_entry = frappe.get_doc(
			"Payment Entry", {"party_name": "_Test Supplier", "paid_from": "_Test Bank Clearance - _TC"}
		)

		if payment_entry.docstatus == 1:
			payment_entry.cancel()
			payment_entry.delete()

		loan = frappe.get_doc("Loan", {"applicant": "_Test Customer"})

		ld_doc = frappe.get_doc("Loan Disbursement", {"against_loan": loan.name})

		if ld_doc.docstatus == 1:
			ld_doc.cancel()
			ld_doc.delete()

		lr_doc = frappe.get_doc("Loan Repayment", {"against_loan": loan.name})

		if lr_doc.docstatus == 1:
			lr_doc.cancel()
			lr_doc.delete()

		lia = frappe.get_doc("Loan Interest Accrual", {"loan": loan.name})
		lia.delete()

		plia = frappe.get_doc("Process Loan Interest Accrual", {"loan": loan.name})

		if plia.docstatus == 1:
			plia.cancel()
			plia.delete()

		loan.load_from_db()
		loan.cancel()
		loan.flags.ignore_links = True
		loan.delete()

		frappe.db.set_single_value("Accounts Settings", "delete_linked_ledger_entries", 0)

	# Basic test case to test if bank clearance tool doesn't break
	# Detailed test can be added later
	def test_bank_clearance(self):
		bank_clearance = frappe.get_doc("Bank Clearance")
		bank_clearance.account = "_Test Bank Clearance - _TC"
		bank_clearance.from_date = add_months(getdate(), -1)
		bank_clearance.to_date = getdate()
		bank_clearance.get_payment_entries()
		self.assertEqual(len(bank_clearance.payment_entries), 3)


def make_bank_account():
	if not frappe.db.get_value("Account", "_Test Bank Clearance - _TC"):
		frappe.get_doc(
			{
				"doctype": "Account",
				"account_type": "Bank",
				"account_name": "_Test Bank Clearance",
				"company": "_Test Company",
				"parent_account": "Bank Accounts - _TC",
			}
		).insert()


def create_loan_masters():
	create_loan_type(
		"Clearance Loan",
		2000000,
		13.5,
		25,
		0,
		5,
		"Cash",
		"_Test Bank Clearance - _TC",
		"_Test Bank Clearance - _TC",
		"Loan Account - _TC",
		"Interest Income Account - _TC",
		"Penalty Income Account - _TC",
	)


def add_transactions():
	make_payment_entry()
	make_loan()


def make_loan():
	loan = create_loan(
		"_Test Customer",
		"Clearance Loan",
		280000,
		"Repay Over Number of Periods",
		20,
		applicant_type="Customer",
	)
	loan.submit()
	make_loan_disbursement_entry(loan.name, loan.loan_amount, disbursement_date=getdate())
	repayment_entry = create_repayment_entry(loan.name, "_Test Customer", getdate(), loan.loan_amount)
	repayment_entry.save()
	repayment_entry.submit()


def make_payment_entry():
	pi = make_purchase_invoice(supplier="_Test Supplier", qty=1, rate=690)
	pe = get_payment_entry("Purchase Invoice", pi.name, bank_account="_Test Bank Clearance - _TC")
	pe.reference_no = "Conrad Oct 18"
	pe.reference_date = "2018-10-24"
	pe.insert()
	pe.submit()
