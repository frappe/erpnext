# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import today

from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.report.dimension_wise_accounts_balance_report.dimension_wise_accounts_balance_report import (
	execute,
)
from erpnext.accounts.utils import get_fiscal_year
from erpnext.tests.utils import ERPNextTestSuite


class TestDimensionWiseAccountsBalance(ERPNextTestSuite):
	"""Balances accounts one column per value of an accounting dimension (here
	Cost Center). Locks the two behaviours that matter: an entry lands in its
	own dimension column as debit - credit, and children roll up into parents."""

	def setUp(self):
		frappe.set_user("Administrator")
		self.company = "_Test Company"
		self.expense_account = "_Test Account Cost for Goods Sold - _TC"
		self.cash_account = "Cash - _TC"

	def _make_cost_center(self, name):
		full_name = f"{name} - _TC"
		if not frappe.db.exists("Cost Center", full_name):
			frappe.get_doc(
				{
					"doctype": "Cost Center",
					"cost_center_name": name,
					"parent_cost_center": "_Test Company - _TC",
					"company": self.company,
					"is_group": 0,
				}
			).insert()
		return full_name

	def _filters(self, **overrides):
		filters = frappe._dict(
			{
				"company": self.company,
				"dimension": "Cost Center",
				"fiscal_year": get_fiscal_year(today(), company=self.company)[0],
			}
		)
		filters.update(overrides)
		return filters

	def test_dimension_column_and_rollup(self):
		# a dedicated cost center isolates our column from any other posted data
		cost_center = self._make_cost_center("Test Dimension CC")
		make_journal_entry(
			self.expense_account,
			self.cash_account,
			300,
			cost_center=cost_center,
			posting_date=today(),
			submit=True,
		)

		columns, data = execute(self._filters())
		column = frappe.scrub(cost_center)
		self.assertIn(column, [c["fieldname"] for c in columns])

		rows = {row["account"]: row for row in data}

		# the entry shows as debit - credit under its own dimension column
		self.assertEqual(rows[self.expense_account][column], 300.0)
		self.assertEqual(rows[self.cash_account][column], -300.0)

		# and rolls up into each account's parent (isolated to our cost center)
		expense_parent = frappe.db.get_value("Account", self.expense_account, "parent_account")
		cash_parent = frappe.db.get_value("Account", self.cash_account, "parent_account")
		self.assertEqual(rows[expense_parent][column], 300.0)
		self.assertEqual(rows[cash_parent][column], -300.0)

	def test_user_sees_only_permitted_dimension_values(self):
		permitted = self._make_cost_center("Test Dimension Permitted CC")
		for cost_center, amount in ((permitted, 400), ("Main - _TC", 1000)):
			make_journal_entry(
				self.expense_account, self.cash_account, amount, cost_center=cost_center, submit=True
			)
		user = make_user_restricted_to_cost_center(permitted)

		frappe.set_user(user)
		try:
			columns, data = execute(self._filters())
		finally:
			frappe.set_user("Administrator")

		self.assertNotIn(frappe.scrub("Main - _TC"), [column["fieldname"] for column in columns])
		rows = {row["account"]: row for row in data}
		self.assertEqual(rows[self.expense_account]["total"], 400)

	def test_finance_book_filter(self):
		cost_center = self._make_cost_center("Test Dimension Finance Book CC")
		finance_book = make_finance_book("_Test Dimension Finance Book")
		jv = make_journal_entry(
			self.expense_account, self.cash_account, 500, cost_center=cost_center, save=False
		)
		jv.finance_book = finance_book
		jv.submit()
		column = frappe.scrub(cost_center)

		def balance(**filters):
			data = execute(self._filters(**filters))[1]
			return next((row[column] for row in data if row["account"] == self.expense_account), 0)

		self.assertEqual(balance(), 0)
		self.assertEqual(balance(finance_book=finance_book), 500)

	def test_requires_fiscal_year(self):
		filters = self._filters()
		filters.pop("fiscal_year")
		self.assertRaises(frappe.ValidationError, execute, filters)


def make_user_restricted_to_cost_center(cost_center):
	user = "test_dimension_wise_balance@example.com"
	if not frappe.db.exists("User", user):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": user,
				"first_name": "Dimension-wise Balance",
				"roles": [{"role": "Accounts User"}],
			}
		).insert()
	frappe.permissions.add_user_permission("Cost Center", cost_center, user)
	return user


def make_finance_book(name):
	if not frappe.db.exists("Finance Book", name):
		frappe.get_doc({"doctype": "Finance Book", "finance_book_name": name}).insert()
	return name
