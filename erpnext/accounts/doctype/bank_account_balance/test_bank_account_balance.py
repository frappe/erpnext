# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.doctype.bank_account.bank_account import set_closing_balance_as_per_statement
from erpnext.tests.permission_test_utils import make_bank_account
from erpnext.tests.utils import ERPNextTestSuite


class TestBankAccountBalance(ERPNextTestSuite):
	def test_duplicate_balance_and_update(self):
		self.addCleanup(frappe.db.rollback)
		bank_account = make_bank_account("_Test Closing Balance", "_Test Company", "HDFC - _TC")
		balance = frappe.get_doc(
			{
				"doctype": "Bank Account Balance",
				"bank_account": bank_account,
				"date": "2026-04-15",
				"balance": 5000,
			}
		).insert()

		with self.assertRaises(frappe.DuplicateEntryError):
			frappe.copy_doc(balance).insert()

		set_closing_balance_as_per_statement(bank_account, balance.date, 9000)
		self.assertEqual(balance.reload().balance, 9000)
		self.assertEqual(
			frappe.db.count("Bank Account Balance", {"bank_account": bank_account, "date": balance.date}),
			1,
		)
		frappe.copy_doc(balance).update({"date": "2026-04-16"}).insert()
