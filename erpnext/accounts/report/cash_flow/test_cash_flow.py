# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, getdate, today

from erpnext.accounts.report.cash_flow.cash_flow import execute
from erpnext.accounts.report.financial_statements import build_period_list, is_dimension_grouped
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

	def test_group_by_dimension(self):
		"""Cash movements must land in their own cost center's column, not just the overall total."""
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry

		cc1, cc2 = "_Test Cost Center - _TC", "_Test Cost Center 2 - _TC"

		filters = frappe._dict(
			company=self.company,
			period_start_date=getdate(),
			period_end_date=getdate(),
			filter_based_on="Date Range",
			periodicity="Yearly",
			accumulated_values=False,
			group_by_dimension="Cost Center",
		)

		period_list = build_period_list(filters)
		self.assertTrue(is_dimension_grouped(period_list))

		def key_for(cost_center):
			return next(p.key for p in period_list if p.dimension_value == cost_center)

		def net_change_row():
			rows = execute(filters)[1]
			return next((row for row in rows if row.get("section") == "'Net Change in Cash'"), {})

		before = net_change_row()

		# cash sales: 400 via cc1, 200 via cc2
		make_journal_entry(
			"Cash - _TC", "Sales - _TC", 400, cost_center=cc1, posting_date=today(), submit=True
		)
		make_journal_entry(
			"Cash - _TC", "Sales - _TC", 200, cost_center=cc2, posting_date=today(), submit=True
		)

		after = net_change_row()

		self.assertEqual(after.get(key_for(cc1), 0) - before.get(key_for(cc1), 0), 400)
		self.assertEqual(after.get(key_for(cc2), 0) - before.get(key_for(cc2), 0), 200)
		self.assertEqual(after.get("total", 0) - before.get("total", 0), 600)

	def test_opening_entries_are_not_cash_flows(self):
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry

		before = self.net_change_in_cash()
		opening_entry = make_journal_entry(
			"Office Equipment - _TC", "Temporary Opening - _TC", 800, posting_date=today(), save=False
		)
		opening_entry.is_opening = "Yes"
		opening_entry.submit()

		self.assertEqual(self.net_change_in_cash() - before, 0)

	def test_date_range_across_fiscal_years_keeps_earlier_profit(self):
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry

		year_start_date = get_fiscal_year(today(), company=self.company)[1]
		filters = frappe._dict(
			company=self.company,
			period_start_date=add_days(year_start_date, -30),
			period_end_date=getdate(),
			filter_based_on="Date Range",
			periodicity="Yearly",
			accumulated_values=0,
		)

		def net_change_in_cash():
			rows = execute(filters)[1]
			return next(row for row in rows if row.get("section") == "'Net Change in Cash'")["total"]

		before = net_change_in_cash()
		make_journal_entry(
			"Cash - _TC", "Sales - _TC", 500, posting_date=add_days(year_start_date, -10), submit=True
		)

		self.assertEqual(net_change_in_cash() - before, 500)

	def test_opening_balance_is_cash_balance_before_period(self):
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry

		fiscal_year, year_start_date, year_end_date = get_fiscal_year(today(), company=self.company)
		filters = frappe._dict(
			company=self.company,
			from_fiscal_year=fiscal_year,
			to_fiscal_year=fiscal_year,
			period_start_date=year_start_date,
			period_end_date=year_end_date,
			filter_based_on="Fiscal Year",
			periodicity="Yearly",
			show_opening_and_closing_balance=1,
		)

		def opening_balance():
			rows = execute(filters)[1]
			return next(row for row in rows if row.get("section") == "Opening")["total"]

		before = opening_balance()
		make_journal_entry(
			"Cash - _TC", "Sales - _TC", 500, posting_date=add_days(year_start_date, -10), submit=True
		)

		self.assertEqual(opening_balance() - before, 500)

	def test_summary_with_accumulated_values_counts_movement_once(self):
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry

		fiscal_year, year_start_date, year_end_date = get_fiscal_year(today(), company=self.company)
		filters = frappe._dict(
			company=self.company,
			from_fiscal_year=fiscal_year,
			to_fiscal_year=fiscal_year,
			period_start_date=year_start_date,
			period_end_date=year_end_date,
			filter_based_on="Fiscal Year",
			periodicity="Quarterly",
			accumulated_values=1,
		)

		def net_change_card():
			summary = execute(filters)[4]
			return next(card["value"] for card in summary if card["label"] == "Net Change in Cash")

		before = net_change_card()
		make_journal_entry("Cash - _TC", "Sales - _TC", 500, posting_date=year_start_date, submit=True)

		self.assertEqual(net_change_card() - before, 500)
