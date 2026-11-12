# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.report.gross_and_net_profit_report.gross_and_net_profit_report import execute

BANK = "_Test Bank - _TC"
INCOME_PARENT = "Income - _TC"
# an isolated fiscal year so other accounts contribute nothing to the totals
FY = "_Test Fiscal Year 2049"
DATE = "2049-06-01"


class TestGrossAndNetProfitReport(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def run_report(self, from_fiscal_year=FY, to_fiscal_year=FY, **filters):
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
				**filters,
			}
		)
		return execute(filters)[1]

	def make_account(self, name, parent, include_in_gross):
		account = create_account(account_name=name, parent_account=parent, company="_Test Company")
		frappe.db.set_value("Account", account, "include_in_gross", include_in_gross)
		return account

	def book_income(self, account, amount, posting_date=DATE):
		make_journal_entry(BANK, account, amount, posting_date=posting_date, submit=True)

	def report_row(self, data, account):
		return next(row for row in data if row.get("account") == account)

	def test_date_range_across_fiscal_years_counts_both_years(self):
		income = self.make_account("_Test GNP Range Income", INCOME_PARENT, include_in_gross=1)
		# one yearly period from July to June spans two calendar fiscal years
		self.book_income(income, 1000, posting_date="2049-11-01")
		self.book_income(income, 500, posting_date="2050-02-01")

		data = self.run_report(
			filter_based_on="Date Range",
			period_start_date="2049-07-01",
			period_end_date="2050-06-30",
			to_fiscal_year="_Test Fiscal Year 2050",
		)

		self.assertEqual(self.report_row(data, "'Gross Profit'")["total"], 1500)
		self.assertEqual(self.report_row(data, "'Net Profit'")["total"], 1500)
