# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
from frappe.utils import add_days, today

from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.accounts.report.financial_ratios.financial_ratios import (
	avg_ratio_balance,
	execute,
	get_gl_data,
	update_balances,
)
from erpnext.accounts.report.financial_statements import get_period_list
from erpnext.tests.utils import ERPNextTestSuite


class TestFinancialRatios(ERPNextTestSuite):
	def setUp(self):
		self.company = "_Test Company"
		self.abbr = "_TC"

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

	def test_ratios_on_standard_chart_without_group_account_types(self):
		self.make_journal_entry("Debtors", "Sales", 500, party=("Customer", "_Test Customer"))
		self.make_journal_entry("Cost of Goods Sold", "Creditors", 200, party=("Supplier", "_Test Supplier"))
		self.make_journal_entry("Office Rent", "Creditors", 100, party=("Supplier", "_Test Supplier"))

		ratios = self.get_ratios()

		self.assertEqual(ratios["Gross Profit Ratio"], 0.6)
		self.assertEqual(ratios["Net Profit Ratio"], 0.4)
		for ratio in ("Current Ratio", "Quick Ratio", "Debtor Turnover Ratio", "Creditor Turnover Ratio"):
			self.assertGreater(ratios[ratio], 0, ratio)

	def test_ledger_takes_category_of_its_parent_group(self):
		create_account(
			account_name="_Test Prepaid Insurance",
			parent_account=f"Tax Assets - {self.abbr}",
			company=self.company,
		)
		before = self.get_group_balance("Current Asset", "Asset")
		self.make_journal_entry("_Test Prepaid Insurance", "Capital Stock", 400)

		self.assertEqual(self.get_group_balance("Current Asset", "Asset") - before, 400)

	def test_category_takes_precedence_over_account_type(self):
		loan_account = create_account(
			account_name="_Test Supplier Loan",
			parent_account=f"Non-Current Liabilities - {self.abbr}",
			account_type="Payable",
			company=self.company,
		)
		frappe.db.set_value("Account", loan_account, "account_category", "Long-term Borrowings")
		before = self.get_group_balance("Current Liability", "Liability")
		self.make_journal_entry("Cash", "_Test Supplier Loan", 400, party=("Supplier", "_Test Supplier"))

		self.assertEqual(self.get_group_balance("Current Liability", "Liability"), before)

	def test_other_income_is_not_sales_in_a_year_without_sales(self):
		self.make_journal_entry("Cash", "Interest Income", 300)

		self.assertEqual(self.get_group_balance("Direct Income", "Income"), 0)

	def test_net_sales_are_total_income_without_revenue_category(self):
		frappe.db.set_value(
			"Account",
			{"company": self.company, "account_category": "Revenue from Operations"},
			"account_category",
			None,
		)
		self.make_journal_entry("Cash", "Interest Income", 300)
		total_income = self.get_total_income(self.get_report_filters())

		self.assertGreaterEqual(total_income, 300)
		self.assertEqual(self.get_group_balance("Direct Income", "Income"), total_income)

	def test_fixed_asset_turnover_combines_groups_of_same_type(self):
		self.set_account_type("Fixed Assets", "Fixed Asset")
		self.make_group_with_ledger(
			"_Test Solar Power System", "Application of Funds (Assets)", "Fixed Asset", "_Test Solar Panels"
		)
		self.make_group_with_ledger("_Test Plant Group", "Fixed Assets", "Fixed Asset", "_Test Plant")
		self.make_journal_entry("Buildings", "Capital Stock", 10000)
		self.make_journal_entry("_Test Solar Panels", "Capital Stock", 5000)
		self.make_journal_entry("_Test Plant", "Capital Stock", 3000)
		self.make_journal_entry("Cash", "Sales", 36000)

		columns, data = execute(self.get_report_filters())
		ratio_row = next(row for row in data if row.get("ratio") == "Fixed Asset Turnover Ratio")

		self.assertEqual(ratio_row[columns[1]["fieldname"]], 2.0)

	def test_direct_expense_combines_groups_of_same_type(self):
		self.set_account_type("Direct Expenses", "Direct Expense")
		self.make_group_with_ledger("_Test Freight Group", "Expenses", "Direct Expense", "_Test Freight")
		before = self.get_group_balance("Direct Expense", "Expense")
		self.make_journal_entry("Cost of Goods Sold", "Creditors", 200, party=("Supplier", "_Test Supplier"))
		self.make_journal_entry("_Test Freight", "Creditors", 300, party=("Supplier", "_Test Supplier"))

		self.assertEqual(self.get_group_balance("Direct Expense", "Expense") - before, 500)

	def test_income_is_for_the_selected_year_only(self):
		filters = self.get_report_filters()
		self.make_journal_entry("Cash", "Sales", 500)
		before = self.get_total_income(filters)
		self.make_journal_entry("Cash", "Sales", 1000, posting_date=add_days(filters.period_start_date, -10))

		self.assertEqual(self.get_total_income(filters), before)

	def test_income_survives_closing_the_selected_year(self):
		filters = self.get_report_filters()
		self.make_journal_entry("Cash", "Sales", 500)
		before = self.get_total_income(filters)

		period_closing_voucher = frappe.new_doc("Period Closing Voucher")
		period_closing_voucher.update(
			{
				"transaction_date": today(),
				"company": self.company,
				"fiscal_year": filters.from_fiscal_year,
				"period_start_date": filters.period_start_date,
				"period_end_date": filters.period_end_date,
				"cost_center": f"Main - {self.abbr}",
				"closing_account_head": f"Capital Stock - {self.abbr}",
				"remarks": "test",
			}
		)
		period_closing_voucher.submit()

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
		root = next((row for row in income if row.get("account") and not row.get("parent_account")), {})
		return root.get(period_list[0].key, 0)

	def get_ratios(self):
		columns, data = execute(self.get_report_filters())
		return {row["ratio"]: row.get(columns[1]["fieldname"]) for row in data}

	def get_group_balance(self, account_type, root_type):
		filters = self.get_report_filters()
		period_list = self.get_period_list(filters)
		year = period_list[0].key
		root_types = ("Asset", "Liability", "Income", "Expense")
		root_type_data = get_gl_data(filters, period_list, [year])[root_types.index(root_type)]
		group_balance = {}
		update_balances(group_balance, {}, account_type, year, root_type_data, root_type, {})
		return group_balance.get(year, 0)

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

	def make_journal_entry(self, debit_account, credit_account, amount, posting_date=None, party=None):
		journal_entry = frappe.new_doc("Journal Entry")
		journal_entry.posting_date = posting_date or today()
		journal_entry.company = self.company
		party_type, party_name = party or (None, None)
		for account, debit, credit in ((debit_account, amount, 0), (credit_account, 0, amount)):
			account = f"{account} - {self.abbr}"
			is_party_account = frappe.get_cached_value("Account", account, "account_type") in (
				"Receivable",
				"Payable",
			)
			journal_entry.append(
				"accounts",
				{
					"account": account,
					"debit_in_account_currency": debit,
					"credit_in_account_currency": credit,
					"party_type": party_type if is_party_account else None,
					"party": party_name if is_party_account else None,
				},
			)
		journal_entry.insert()
		journal_entry.submit()
