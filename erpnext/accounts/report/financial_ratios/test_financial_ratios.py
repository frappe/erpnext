# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from erpnext.accounts.report.financial_ratios.financial_ratios import (
	execute,
	get_gl_data,
)
from erpnext.accounts.report.financial_statements import get_period_list

test_dependencies = ["Supplier"]


class TestFinancialRatios(FrappeTestCase):
	def setUp(self):
		self.company = "_Test Company"
		self.abbr = "_TC"
		# The report matches the group accounts by their account_type, which the
		# standard chart of accounts does not set on group accounts by default.
		self.set_account_type("Direct Income", "Direct Income")

	def tearDown(self):
		frappe.db.rollback()

	def set_account_type(self, account_name, account_type):
		frappe.db.set_value("Account", f"{account_name} - {self.abbr}", "account_type", account_type)

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
