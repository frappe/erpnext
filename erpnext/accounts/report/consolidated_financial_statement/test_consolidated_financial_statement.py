# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import flt, today

from erpnext.accounts.report.consolidated_financial_statement.consolidated_financial_statement import (
	execute,
)
from erpnext.accounts.utils import get_fiscal_year
from erpnext.tests.utils import ERPNextTestSuite

PARENT_COMPANY = "Parent Group Company India"
CHILD_COMPANY = "Child Company India"


class TestConsolidatedFinancialStatement(ERPNextTestSuite):
	"""Consolidation is exercised via the bootstrap group of companies
	(`Parent Group Company India` with child `Child Company India`). Income and
	expense posted in the child company must surface in the report that is run
	for the parent (group) company."""

	def setUp(self):
		self.fiscal_year = get_fiscal_year(today(), company=PARENT_COMPANY)[0]

	def run_report(self, **extra):
		filters = frappe._dict(
			{
				"company": PARENT_COMPANY,
				"filter_based_on": "Fiscal Year",
				"from_fiscal_year": self.fiscal_year,
				"to_fiscal_year": self.fiscal_year,
				"periodicity": "Yearly",
				"include_default_book_entries": 1,
			}
		)
		filters.update(extra)
		return execute(filters)[1]

	def post_journal_entry(self, debit_account, credit_account, amount):
		je = frappe.new_doc("Journal Entry")
		je.posting_date = today()
		je.company = CHILD_COMPANY
		je.set(
			"accounts",
			[
				{"account": debit_account, "debit_in_account_currency": amount},
				{"account": credit_account, "credit_in_account_currency": amount},
			],
		)
		je.save()
		je.submit()
		return je

	def get_row(self, data, account_name_fragment, last_match=False):
		"""Return the first (or last) row whose account_name contains the fragment.

		Pass ``last_match=True`` to get the leaf/most-specific match when the fragment
		is also a prefix of a parent group account (parents precede children in tree order).
		"""
		found = None
		for row in data:
			if account_name_fragment in str(row.get("account_name") or ""):
				if not last_match:
					return row
				found = row
		return found

	def test_profit_and_loss_reflects_child_company_income(self):
		amount = 7000
		self.post_journal_entry("Cash - CCI", "Sales - CCI", amount)

		data = self.run_report(report="Profit and Loss Statement", accumulated_in_group_company=0)

		self.assertTrue(data, "Report returned no rows")

		# child's Sales account is mapped onto the parent chart (Sales - PGCI)
		sales_row = self.get_row(data, "Sales", last_match=True)
		self.assertIsNotNone(sales_row, "Sales row missing from consolidated P&L")
		# >= so a pre-existing Sales balance in the fiscal year doesn't make this brittle
		self.assertGreaterEqual(flt(sales_row.get(CHILD_COMPANY)), amount)

		total_income_row = self.get_row(data, "Total Income (Credit)")
		self.assertIsNotNone(total_income_row, "Total Income row missing")
		self.assertGreaterEqual(flt(total_income_row.get("total")), amount)

	def test_profit_and_loss_reflects_child_company_expense(self):
		amount = 3000
		self.post_journal_entry("Marketing Expenses - CCI", "Cash - CCI", amount)

		data = self.run_report(report="Profit and Loss Statement", accumulated_in_group_company=0)

		expense_row = self.get_row(data, "Marketing Expenses", last_match=True)
		self.assertIsNotNone(expense_row, "Marketing Expenses row missing from consolidated P&L")
		self.assertGreaterEqual(flt(expense_row.get(CHILD_COMPANY)), amount)

		total_expense_row = self.get_row(data, "Total Expense (Debit)")
		self.assertIsNotNone(total_expense_row, "Total Expense row missing")
		self.assertGreaterEqual(flt(total_expense_row.get("total")), amount)

	def test_accumulated_in_group_company_rolls_up_to_parent(self):
		"""With `accumulated_in_group_company`, the child's amount is also
		accumulated into the parent company column."""
		amount = 5000
		self.post_journal_entry("Cash - CCI", "Sales - CCI", amount)

		data = self.run_report(report="Profit and Loss Statement", accumulated_in_group_company=1)

		sales_row = self.get_row(data, "Sales", last_match=True)
		self.assertIsNotNone(sales_row)
		child_value = flt(sales_row.get(CHILD_COMPANY))
		self.assertGreaterEqual(child_value, amount)
		# parent column picks up the child value when accumulated
		self.assertEqual(flt(sales_row.get(PARENT_COMPANY)), child_value)
		# the total equals the consolidated (group) value, not the sum of parent + child
		# columns -- this is the regression guard for the double-count fix
		self.assertEqual(flt(sales_row.get("total")), child_value)

	def test_balance_sheet_executes_and_returns_rows(self):
		# posting income leaves a balancing entry in the child's Cash (Asset) account
		amount = 4000
		self.post_journal_entry("Cash - CCI", "Sales - CCI", amount)

		data = self.run_report(report="Balance Sheet", accumulated_in_group_company=0)

		self.assertTrue(data, "Balance Sheet returned no rows")
		cash_row = self.get_row(data, "Cash")
		self.assertIsNotNone(cash_row, "Cash asset row missing from consolidated Balance Sheet")
		self.assertGreaterEqual(flt(cash_row.get(CHILD_COMPANY)), amount)
