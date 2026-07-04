# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import today

from erpnext.accounts.report.cash_flow.cash_flow import execute
from erpnext.accounts.utils import get_fiscal_year
from erpnext.tests.utils import ERPNextTestSuite


class TestCashFlow(ERPNextTestSuite):
	def setUp(self):
		self.company = "_Test Company"

	def net_change_in_cash(self):
		"""Run the report for the current fiscal year and return the Net Change in Cash total."""
		fiscal_year, year_start, year_end = get_fiscal_year(today(), company=self.company)
		filters = frappe._dict(
			company=self.company,
			from_fiscal_year=fiscal_year,
			to_fiscal_year=fiscal_year,
			period_start_date=year_start,
			period_end_date=year_end,
			filter_based_on="Fiscal Year",
			periodicity="Yearly",
			accumulated_values=0,
		)
		rows = execute(filters)[1]
		row = next(row for row in rows if row.get("section") == "'Net Change in Cash'")
		return row["total"]

	def test_report_executes(self):
		# Smoke-guards the raw-SQL -> query-builder port: the report query must compile and run on
		# both MariaDB and postgres.
		company = frappe.db.get_value("Company", {}, "name")
		fy = frappe.db.get_value("Fiscal Year", {}, "name", order_by="year_start_date desc")
		columns, *_rest = execute(
			frappe._dict(
				{
					"company": company,
					"from_fiscal_year": fy,
					"to_fiscal_year": fy,
					"filter_based_on": "Fiscal Year",
					"periodicity": "Yearly",
				}
			)
		)
		self.assertTrue(columns)

	def test_cash_sale_increases_net_change_in_cash(self):
		"""A cash sale (debit Cash, credit Income) increases net change in cash by the amount."""
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry

		before = self.net_change_in_cash()
		make_journal_entry("Cash - _TC", "Sales - _TC", 500, posting_date=today(), submit=True)

		self.assertEqual(self.net_change_in_cash() - before, 500)

	def test_cash_purchase_of_asset_is_investing_outflow(self):
		"""Buying a fixed asset for cash is an investing outflow that reduces net change in cash."""
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry

		asset_account = "Office Equipment - _TC"

		before = self.net_change_in_cash()
		# debit the fixed asset, credit cash -> cash goes out
		make_journal_entry(asset_account, "Cash - _TC", 800, posting_date=today(), submit=True)

		self.assertEqual(self.net_change_in_cash() - before, -800)
