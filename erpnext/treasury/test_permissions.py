# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# See license.txt

"""Runs as Accounts User and Accounts Manager, not Administrator, to catch missing permissions."""

import frappe
from frappe.permissions import add_user_permission
from frappe.utils import nowdate

from erpnext.tests.utils import ERPNextTestSuite
from erpnext.treasury.dashboard import get_interest_earned
from erpnext.treasury.doctype.investment.test_investment import (
	TEST_COMPANY,
	create_financial_institution,
	create_investment_type,
	make_investment,
)
from erpnext.treasury.doctype.investment_transaction.test_investment_transaction import (
	INVESTMENT_ACCOUNTS,
	make_transaction,
)
from erpnext.treasury.report.cash_flow_forecast import cash_flow_forecast

ACCOUNTS_USER = "treasury.accountant@example.com"
ACCOUNTS_MANAGER = "treasury.manager@example.com"


class TestTreasuryPermissions(ERPNextTestSuite):
	def setUp(self):
		create_investment_type("_Test Bank FD", "Deposit")
		create_financial_institution("_Test Bank")
		create_user(ACCOUNTS_USER, "Accounts User")
		create_user(ACCOUNTS_MANAGER, "Accounts Manager")

	def test_accounts_user_drafts_and_accounts_manager_approves(self):
		with self.set_user(ACCOUNTS_USER):
			investment = make_investment(**INVESTMENT_ACCOUNTS).insert()
			self.assertRaises(frappe.PermissionError, investment.submit)
		self.assertEqual(frappe.db.get_value("Investment", investment.name, "docstatus"), 0)

		with self.set_user(ACCOUNTS_MANAGER):
			investment.reload()
			investment.submit()
		self.assertEqual(investment.status, "Active")
		self.assertEqual(investment.approved_by, ACCOUNTS_MANAGER)

		with self.set_user(ACCOUNTS_USER):
			make_transaction(investment.name, "Purchase", gross_amount=100000).submit()
		self.assertEqual(frappe.db.get_value("Investment", investment.name, "total_cost"), 100000)

	def test_user_restricted_to_a_company_cannot_read_another(self):
		add_user_permission("Company", TEST_COMPANY, ACCOUNTS_USER)
		filters = {"company": "_Test Company 1", "from_date": nowdate()}

		with self.set_user(ACCOUNTS_USER):
			self.assertRaises(frappe.PermissionError, get_interest_earned, filters)
			self.assertRaises(frappe.PermissionError, cash_flow_forecast.execute, filters)


def create_user(email, role):
	if frappe.db.exists("User", email):
		return

	frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": role,
			"send_welcome_email": 0,
			"roles": [{"role": role}],
		}
	).insert()
