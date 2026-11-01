# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.accounts.report.financial_ratios.financial_ratios import get_gl_data, update_balances
from erpnext.accounts.report.financial_statements import get_period_list


class TestFinancialRatios(FrappeTestCase):
	def setUp(self):
		self.company = "_Test Company"
		self.abbr = "_TC"

	def test_direct_expense_combines_groups_of_same_type(self):
		frappe.db.set_value("Account", f"Direct Expenses - {self.abbr}", "account_type", "Direct Expense")
		self.make_group_with_ledger("_Test Freight Group", "Expenses", "Direct Expense", "_Test Freight")
		before = self.get_direct_expense()
		self.make_journal_entry("Cost of Goods Sold", "Cash", 200)
		self.make_journal_entry("_Test Freight", "Cash", 300)

		self.assertEqual(self.get_direct_expense() - before, 500)

	def get_direct_expense(self):
		filters = self.get_report_filters()
		period_list = get_period_list(
			filters.from_fiscal_year,
			filters.to_fiscal_year,
			filters.period_start_date,
			filters.period_end_date,
			filters.filter_based_on,
			filters.periodicity,
			company=filters.company,
		)
		year = period_list[0].key
		expense = get_gl_data(filters, period_list, [year])[3]
		direct_expense = {}
		update_balances(direct_expense, {}, "Direct Expense", year, expense, "Expense")
		return direct_expense.get(year, 0)

	def get_report_filters(self):
		active_fy = frappe.db.get_value(
			"Fiscal Year",
			{"disabled": 0, "year_start_date": ("<=", today()), "year_end_date": (">=", today())},
			["name", "year_start_date", "year_end_date"],
			as_dict=True,
		)
		return frappe._dict(
			company=self.company,
			from_fiscal_year=active_fy.name,
			to_fiscal_year=active_fy.name,
			period_start_date=active_fy.year_start_date,
			period_end_date=active_fy.year_end_date,
			filter_based_on="Fiscal Year",
			periodicity="Yearly",
		)

	def make_group_with_ledger(self, group_name, parent_name, account_type, ledger_name):
		create_account(
			account_name=group_name,
			parent_account=f"{parent_name} - {self.abbr}",
			account_type=account_type,
			is_group=1,
			company=self.company,
		)
		create_account(
			account_name=ledger_name,
			parent_account=f"{group_name} - {self.abbr}",
			company=self.company,
		)

	def make_journal_entry(self, debit_account, credit_account, amount):
		journal_entry = frappe.new_doc("Journal Entry")
		journal_entry.posting_date = today()
		journal_entry.company = self.company
		for account, debit, credit in (
			(debit_account, amount, 0),
			(credit_account, 0, amount),
		):
			journal_entry.append(
				"accounts",
				{
					"account": f"{account} - {self.abbr}",
					"debit_in_account_currency": debit,
					"credit_in_account_currency": credit,
				},
			)
		journal_entry.insert()
		journal_entry.submit()
