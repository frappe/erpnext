# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import add_months, getdate

from erpnext.accounts.doctype.payment_entry.test_payment_entry import get_payment_entry
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice


class TestBankClearance(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		make_bank_account()
		add_transactions()

	# Basic test case to test if bank clearance tool doesn't break
	# Detailed test can be added later
	def test_bank_clearance(self):
		bank_clearance = frappe.get_doc("Bank Clearance")
		bank_clearance.account = "_Test Bank Clearance - _TC"
		bank_clearance.from_date = add_months(getdate(), -1)
		bank_clearance.to_date = getdate()
		bank_clearance.get_payment_entries()
		self.assertEqual(len(bank_clearance.payment_entries), 1)


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


def add_transactions():
	make_payment_entry()


def make_payment_entry():
	pi = make_purchase_invoice(supplier="_Test Supplier", qty=1, rate=690)
	pe = get_payment_entry("Purchase Invoice", pi.name, bank_account="_Test Bank Clearance - _TC")
	pe.reference_no = "Conrad Oct 18"
	pe.reference_date = "2018-10-24"
	pe.insert()
	pe.submit()
