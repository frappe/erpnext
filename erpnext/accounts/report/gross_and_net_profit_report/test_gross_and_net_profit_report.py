# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.report.gross_and_net_profit_report.gross_and_net_profit_report import execute
from erpnext.tests.utils import ERPNextTestSuite

BANK = "_Test Bank - _TC"
INCOME_PARENT = "Income - _TC"
EXPENSE_PARENT = "Expenses - _TC"
# bootstrap leaf accounts that already have include_in_gross = 0 (no creation needed)
NON_GROSS_INCOME = "_Test Account Sales - _TC"
NON_GROSS_EXPENSE = "_Test Account Cost for Goods Sold - _TC"
# an isolated fiscal year so other accounts contribute nothing to the totals
FY = "_Test Fiscal Year 2049"
DATE = "2049-06-01"


class TestGrossAndNetProfitReport(ERPNextTestSuite):
	def run_report(self, from_fiscal_year=FY, to_fiscal_year=FY):
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"filter_based_on": "Fiscal Year",
				"from_fiscal_year": from_fiscal_year,
				"to_fiscal_year": to_fiscal_year,
				"period_start_date": "2049-01-01",
				"period_end_date": "2049-12-31",
				"periodicity": "Yearly",
				"accumulated_values": 0,
				"presentation_currency": None,
			}
		)
		return execute(filters)[1]

	def make_account(self, name, parent, include_in_gross):
		account = create_account(account_name=name, parent_account=parent, company="_Test Company")
		frappe.db.set_value("Account", account, "include_in_gross", include_in_gross)
		return account

	def book_income(self, account, amount):
		make_journal_entry(BANK, account, amount, posting_date=DATE, submit=True)

	def book_expense(self, account, amount):
		make_journal_entry(account, BANK, amount, posting_date=DATE, submit=True)

	def report_row(self, data, account):
		return next(row for row in data if row.get("account") == account)

	def test_gross_profit_excludes_non_gross_accounts(self):
		# reuse bootstrap accounts for the non-gross (include_in_gross = 0) side
		gross_income = self.make_account("_Test GNP Gross Income", INCOME_PARENT, include_in_gross=1)
		gross_expense = self.make_account("_Test GNP Gross Expense", EXPENSE_PARENT, include_in_gross=1)

		self.book_income(gross_income, 10000)
		self.book_income(NON_GROSS_INCOME, 2000)
		self.book_expense(gross_expense, 4000)
		self.book_expense(NON_GROSS_EXPENSE, 1000)

		data = self.run_report()
		# gross profit only counts include_in_gross accounts: 10000 - 4000
		self.assertEqual(self.report_row(data, "'Gross Profit'")["total"], 6000)
		# net profit counts everything: (10000 + 2000) - (4000 + 1000)
		self.assertEqual(self.report_row(data, "'Net Profit'")["total"], 7000)

	def test_net_profit_equals_gross_when_all_included(self):
		income = self.make_account("_Test GNP All Income", INCOME_PARENT, include_in_gross=1)
		expense = self.make_account("_Test GNP All Expense", EXPENSE_PARENT, include_in_gross=1)

		self.book_income(income, 9000)
		self.book_expense(expense, 5000)

		data = self.run_report()
		self.assertEqual(self.report_row(data, "'Gross Profit'")["total"], 4000)
		self.assertEqual(self.report_row(data, "'Net Profit'")["total"], 4000)

	def test_nothing_included_in_gross_when_no_entries(self):
		# a fiscal year with no income/expense entries yields the placeholder row
		data = self.run_report(
			from_fiscal_year="_Test Fiscal Year 2048", to_fiscal_year="_Test Fiscal Year 2048"
		)
		self.assertEqual(data[0]["account"], "'Nothing is included in gross'")
