# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
from frappe.utils import add_days, today

from erpnext.accounts.report.financial_ratios.financial_ratios import (
	avg_ratio_balance,
	execute,
	get_gl_data,
)
from erpnext.accounts.report.financial_statements import get_period_list
from erpnext.tests.utils import ERPNextTestSuite


class TestFinancialRatios(ERPNextTestSuite):
	def setUp(self):
		self.company = "_Test Company"
		self.abbr = "_TC"
		# The report matches the group accounts by their account_type, which the
		# standard chart of accounts does not set on group accounts by default.
		self.set_account_type("Fixed Assets", "Fixed Asset")
		self.set_account_type("Direct Income", "Direct Income")

	def set_account_type(self, account_name, account_type):
		frappe.db.set_value("Account", f"{account_name} - {self.abbr}", "account_type", account_type)

	def test_fixed_asset_turnover_uses_net_fixed_assets(self):
		# Acquire a fixed asset worth 10,000 funded by equity.
		self.make_journal_entry("Buildings", "Capital Stock", 10000)
		# Book sales of 20,000 collected in cash. Total assets now = 30,000
		# (Buildings 10,000 + Cash 20,000), while net fixed assets stay at 10,000.
		self.make_journal_entry("Cash", "Sales", 20000)

		columns, data = execute(self.get_report_filters())
		year_key = columns[1]["fieldname"]
		ratio_row = next((row for row in data if row.get("ratio") == "Fixed Asset Turnover Ratio"), None)
		self.assertIsNotNone(ratio_row, "Fixed Asset Turnover Ratio row not found in report output")

		# Net Sales / Net Fixed Assets = 20,000 / 10,000 = 2.0
		# (the old behaviour divided by total assets, giving 20,000 / 30,000 = 0.667)
		self.assertEqual(ratio_row[year_key], 2.0)

	def test_creditor_turnover_is_positive(self):
		self.set_account_type("Direct Expenses", "Direct Expense")
		self.make_journal_entry("Cost of Goods Sold", "Creditors", 200, supplier="_Test Supplier")

		columns, data = execute(self.get_report_filters())
		ratio_row = next(row for row in data if row.get("ratio") == "Creditor Turnover Ratio")

		self.assertGreater(ratio_row[columns[1]["fieldname"]], 0)

	def test_income_is_for_the_selected_year_only(self):
		filters = self.get_report_filters()
		self.make_journal_entry("Cash", "Sales", 500)
		before = self.get_total_income(filters)
		self.make_journal_entry("Cash", "Sales", 1000, posting_date=add_days(filters.period_start_date, -10))

		self.assertEqual(self.get_total_income(filters), before)

	def test_average_debtors_in_company_currency(self):
		filters = self.get_report_filters()
		period_key = self.get_period_list(filters)[0].key

		def average_debtors():
			return avg_ratio_balance("Receivable", self.get_period_list(filters), 2, filters)[period_key]

		before = average_debtors()
		journal_entry = frappe.new_doc("Journal Entry")
		journal_entry.update({"posting_date": today(), "company": self.company, "multi_currency": 1})
		journal_entry.append(
			"accounts",
			{
				"account": "_Test Receivable USD - _TC",
				"party_type": "Customer",
				"party": "_Test Customer USD",
				"exchange_rate": 80,
				"debit_in_account_currency": 100,
			},
		)
		journal_entry.append("accounts", {"account": "Sales - _TC", "credit_in_account_currency": 8000})
		journal_entry.submit()

		self.assertEqual(average_debtors() - before, 4000)

	def get_period_list(self, filters):
		return get_period_list(
			filters.from_fiscal_year,
			filters.to_fiscal_year,
			filters.period_start_date,
			filters.period_end_date,
			filters.filter_based_on,
			filters.periodicity,
			company=filters.company,
		)

	def get_total_income(self, filters):
		period_list = self.get_period_list(filters)
		income = get_gl_data(filters, period_list, [])[2]
		return next(row for row in income if row.get("account") and not row.get("parent_account"))[
			period_list[0].key
		]

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

	def make_journal_entry(self, debit_account, credit_account, amount, posting_date=None, supplier=None):
		journal_entry = frappe.new_doc("Journal Entry")
		journal_entry.posting_date = posting_date or today()
		journal_entry.company = self.company
		for account, debit, credit, party in (
			(debit_account, amount, 0, None),
			(credit_account, 0, amount, supplier),
		):
			journal_entry.append(
				"accounts",
				{
					"account": f"{account} - {self.abbr}",
					"debit_in_account_currency": debit,
					"credit_in_account_currency": credit,
					"party_type": "Supplier" if party else None,
					"party": party,
				},
			)
		journal_entry.insert()
		journal_entry.submit()
