# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import today

from erpnext.accounts.doctype.bank_account.bank_account import set_closing_balance_as_per_statement
from erpnext.tests.permission_test_utils import (
	as_user,
	assert_refused_for_names,
	make_bank_account,
	make_company_fenced_user,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestBankAccount(ERPNextTestSuite):
	def test_closing_balance_fences_the_bank_account(self):
		bank_account = make_bank_account("UP Closing Balance", "_Test Company", "HDFC - _TC")

		def closing_balance_kwargs(name):
			return {"bank_account": name, "date": today(), "balance": 10}

		outside = make_company_fenced_user("ba-fenced@example.com", ["Accounts User"], "_Test Company 1")
		with as_user(outside):
			assert_refused_for_names(
				self,
				set_closing_balance_as_per_statement,
				closing_balance_kwargs,
				[bank_account],
				type_gated=True,
				caller_supplied=True,
			)
		inside = make_company_fenced_user("ba-fenced@example.com", ["Accounts User"], "_Test Company")
		with as_user(inside):
			set_closing_balance_as_per_statement(bank_account, today(), 10)
		self.assertEqual(
			frappe.db.get_value(
				"Bank Account Balance", {"bank_account": bank_account, "date": today()}, "balance"
			),
			10,
		)
