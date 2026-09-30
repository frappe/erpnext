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

	def test_requires_fiscal_year(self):
		filters = self._filters()
		filters.pop("fiscal_year")
		self.assertRaises(frappe.ValidationError, execute, filters)
