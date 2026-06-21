# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
from frappe.utils import today

from erpnext.accounts.report.financial_ratios.financial_ratios import execute
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
