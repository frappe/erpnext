# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from itertools import pairwise
from unittest.mock import patch

import frappe
from frappe.utils import add_days, getdate, today

from erpnext.accounts.report.cash_flow.cash_flow import execute
from erpnext.accounts.report.financial_statements import build_period_list, is_dimension_grouped
from erpnext.accounts.utils import get_fiscal_year
from erpnext.tests.utils import ERPNextTestSuite


class TestCashFlow(ERPNextTestSuite):
	def setUp(self):
		self.company = "_Test Company"

	def run_report(self, **extra):
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
			**extra,
		)
		return execute(filters)[1]

	def get_row(self, label, **extra):
		rows = self.run_report(**extra)
		return next(row for row in rows if label in str(row.get("section_name") or row.get("account_name")))

	def net_change_in_cash(self):
		"""Run the report for the current fiscal year and return the Net Change in Cash total."""
		rows = self.run_report()
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

	def test_presentation_currency_converts_account_type_rows(self):
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry

		make_journal_entry("Office Equipment - _TC", "Cash - _TC", 4000, posting_date=today(), submit=True)

		with patch("erpnext.accounts.report.utils.get_rate_as_at", return_value=80):
			row = self.get_row("Net Change in Fixed Asset", presentation_currency="USD")

		self.assertEqual(row["total"], self.get_row("Net Change in Fixed Asset")["total"] / 80)
		self.assertEqual(row["currency"], "USD")

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

	def test_accumulated_totals_across_fiscal_years_keep_earlier_years(self):
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry

		fiscal_year, year_start_date, year_end_date = get_fiscal_year(today(), company=self.company)
		previous_fiscal_year, previous_year_start_date, _end = get_fiscal_year(
			add_days(year_start_date, -1), company=self.company
		)
		filters = frappe._dict(
			company=self.company,
			from_fiscal_year=previous_fiscal_year,
			to_fiscal_year=fiscal_year,
			period_start_date=previous_year_start_date,
			period_end_date=year_end_date,
			filter_based_on="Fiscal Year",
			periodicity="Yearly",
			accumulated_values=1,
		)

		def investing_card_and_net_change_total():
			_columns, rows, _message, _chart, summary = execute(filters)
			card = next(card["value"] for card in summary if card["label"] == "Net Cash from Investing")
			net_change = next(row for row in rows if row.get("section") == "'Net Change in Cash'")
			return card, net_change["total"]

		before_card, before_total = investing_card_and_net_change_total()
		for posting_date in (previous_year_start_date, year_start_date):
			make_journal_entry(
				"Office Equipment - _TC", "Cash - _TC", 500, posting_date=posting_date, submit=True
			)
			make_journal_entry("Cash - _TC", "Sales - _TC", 300, posting_date=posting_date, submit=True)

		card, total = investing_card_and_net_change_total()
		self.assertEqual(card - before_card, -1000)
		self.assertEqual(total - before_total, -400)

	def test_opening_and_closing_balance_by_dimension(self):
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry

		cc1, cc2 = "_Test Cost Center - _TC", "_Test Cost Center 2 - _TC"
		fiscal_year, year_start_date, year_end_date = get_fiscal_year(today(), company=self.company)
		filters = frappe._dict(
			company=self.company,
			from_fiscal_year=fiscal_year,
			to_fiscal_year=fiscal_year,
			period_start_date=year_start_date,
			period_end_date=year_end_date,
			filter_based_on="Fiscal Year",
			periodicity="Quarterly",
			accumulated_values=0,
			group_by_dimension="Cost Center",
			show_opening_and_closing_balance=1,
		)
		period_list = build_period_list(filters)

		def book_cash_sale(cost_center, amount, posting_date):
			make_journal_entry(
				"Cash - _TC",
				"Sales - _TC",
				amount,
				cost_center=cost_center,
				posting_date=posting_date,
				submit=True,
			)

		def keys_for(cost_center):
			return [p.key for p in period_list if p.dimension_value == cost_center]

		def opening_and_closing_rows():
			rows = execute(filters)[1]
			opening = next(row for row in rows if row.get("section") == "Opening")
			closing = next(row for row in rows if row.get("section") == "Closing (Opening + Total)")
			return opening, closing

		def balances():
			"""(opening, closing) for each cost center and for the Total column."""
			opening, closing = opening_and_closing_rows()
			result = {"total": (opening["total"], closing["total"])}
			for cost_center in (cc1, cc2):
				keys = keys_for(cost_center)
				result[cost_center] = (opening[keys[0]], closing[keys[-1]])
			return result

		before = balances()

		# last year: 300 cash in cc1, 500 in cc2 -> their opening cash
		last_year = add_days(year_start_date, -10)
		book_cash_sale(cc1, 300, last_year)
		book_cash_sale(cc2, 500, last_year)

		# this year: 100 more cash in cc1
		book_cash_sale(cc1, 100, today())

		after = balances()

		def change(name):
			return tuple(a - b for a, b in zip(after[name], before[name], strict=True))

		# (opening, closing)
		self.assertEqual(change(cc1), (300, 400))
		self.assertEqual(change(cc2), (500, 500))  # its own opening, not cc1's closing
		self.assertEqual(change("total"), (800, 900))

		# within a cost center, each quarter opens with the previous quarter's closing
		opening, closing = opening_and_closing_rows()
		for cost_center in (cc1, cc2):
			for previous, current in pairwise(keys_for(cost_center)):
				self.assertEqual(opening[current], closing[previous])
