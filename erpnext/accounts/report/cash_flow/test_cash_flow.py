# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, today

from erpnext.accounts.report.cash_flow.cash_flow import execute
from erpnext.accounts.utils import get_fiscal_year


class TestCashFlow(FrappeTestCase):
	def setUp(self):
		self.company = "_Test Company"

	def tearDown(self):
		frappe.db.rollback()

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

	def test_opening_entries_are_not_cash_flows(self):
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry

		before = self.net_change_in_cash()
		opening_entry = make_journal_entry(
			"Office Equipments - _TC", "Temporary Opening - _TC", 800, posting_date=today(), save=False
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

	def test_opening_cash_entry_on_the_first_day_is_in_the_opening_balance(self):
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

		def opening_and_closing():
			rows = execute(filters)[1]
			opening = next(row for row in rows if row.get("section") == "Opening")["total"]
			closing = next(row for row in rows if row.get("section") == "Closing (Opening + Total)")["total"]
			return opening, closing

		before_opening, before_closing = opening_and_closing()
		opening_entry = make_journal_entry(
			"Cash - _TC", "Temporary Opening - _TC", 500, posting_date=year_start_date, save=False
		)
		opening_entry.is_opening = "Yes"
		opening_entry.submit()

		opening, closing = opening_and_closing()
		self.assertEqual(opening - before_opening, 500)
		self.assertEqual(closing - before_closing, 500)

		late_opening_entry = make_journal_entry(
			"Cash - _TC", "Temporary Opening - _TC", 300, posting_date=add_days(year_end_date, 1), save=False
		)
		late_opening_entry.is_opening = "Yes"
		late_opening_entry.submit()

		self.assertEqual(opening_and_closing(), (opening + 300, closing + 300))
