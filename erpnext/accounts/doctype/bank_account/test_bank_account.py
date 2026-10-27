# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import unittest

import frappe
from frappe.utils import today

from erpnext.accounts.doctype.bank_account.bank_account import set_closing_balance_as_per_statement
from erpnext.tests.permission_test_utils import (
	MISSING_NAME,
	as_user,
	assert_refused_for_names,
	assert_refused_without,
	make_bank_account,
	make_company_fenced_user,
	make_fenced_user,
	make_other_company_bank_account,
)
from erpnext.tests.utils import ERPNextTestSuite

FENCED_USER = "_test_bank_account_fenced_user@example.com"
ACCOUNTS_USER = "_test_bank_account_accounts_user@example.com"


class TestBankAccount(ERPNextTestSuite):
	def setUp(self):
		self.bank_account = make_bank_account("_Test UP Own", "_Test Company", "_Test Bank - _TC")
		self.second_bank_account = make_bank_account(
			"_Test UP Second", "_Test Company", "_Test Bank USD - _TC"
		)
		self.other_bank_account = make_other_company_bank_account()

	def assert_refused_for_bank_accounts(self, user, forbidden):
		def for_bank_account(name):
			return {"bank_account": name, "date": today(), "balance": 500}

		account, company = frappe.db.get_value("Bank Account", forbidden, ["account", "company"])
		with as_user(user):
			assert_refused_without(
				self, [account, company], set_closing_balance_as_per_statement, **for_bank_account(forbidden)
			)
			assert_refused_for_names(
				self,
				set_closing_balance_as_per_statement,
				for_bank_account,
				[],
				type_gated=True,
				caller_supplied=True,
			)
		for bank_account in (forbidden, MISSING_NAME):
			self.assertFalse(frappe.db.exists("Bank Account Balance", {"bank_account": bank_account}))

	def assert_balance_set(self, user, bank_account, balance):
		with as_user(user):
			set_closing_balance_as_per_statement(bank_account, today(), balance)
		self.assertEqual(
			frappe.db.get_value(
				"Bank Account Balance", {"bank_account": bank_account, "date": today()}, "balance"
			),
			balance,
		)

	def test_set_closing_balance_refuses_bank_account_outside_company_fence(self):
		fenced = make_company_fenced_user(FENCED_USER, ["Accounts User"], "_Test Company")
		accounts_user = make_fenced_user(ACCOUNTS_USER, ["Accounts User"])

		self.assert_refused_for_bank_accounts(fenced, self.other_bank_account)
		self.assert_balance_set(fenced, self.bank_account, 500)
		self.assert_balance_set(accounts_user, self.other_bank_account, 700)

	def test_set_closing_balance_refuses_bank_account_outside_bank_account_fence(self):
		fenced = make_fenced_user(FENCED_USER, ["Accounts User"], [("Bank Account", self.bank_account)])
		accounts_user = make_fenced_user(ACCOUNTS_USER, ["Accounts User"])

		self.assert_refused_for_bank_accounts(fenced, self.second_bank_account)
		self.assert_balance_set(fenced, self.bank_account, 500)
		self.assert_balance_set(accounts_user, self.second_bank_account, 800)
