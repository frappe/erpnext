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

	def test_accumulated_date_range_counts_only_movements_in_range(self):
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry

		_fiscal_year, year_start_date, year_end_date = get_fiscal_year(today(), company=self.company)
		range_start_date = add_days(year_start_date, 90)
		filters = frappe._dict(
			company=self.company,
			period_start_date=range_start_date,
			period_end_date=year_end_date,
			filter_based_on="Date Range",
			periodicity="Quarterly",
			accumulated_values=1,
		)

		def net_change_in_cash():
			columns, rows = execute(filters)[:2]
			net_change = next(row for row in rows if row.get("section") == "'Net Change in Cash'")
			return [
				net_change[column["fieldname"]] for column in columns if column["fieldtype"] == "Currency"
			]

		before = net_change_in_cash()
		for amount, posting_date in ((1000, year_start_date), (500, range_start_date)):
			make_journal_entry(
				"Cash - _TC", "Capital Stock - _TC", amount, posting_date=posting_date, submit=True
			)

		self.assertEqual(
			[
				round(after - previous, 2)
				for after, previous in zip(net_change_in_cash(), before, strict=True)
			],
			[500] * len(before),
		)

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
			periodicity="Quarterly",
			accumulated_values=1,
			show_opening_and_closing_balance=1,
		)

		def report_values():
			columns, rows, _message, _chart, summary = execute(filters)
			card = next(card["value"] for card in summary if card["label"] == "Net Cash from Investing")
			net_change = next(row for row in rows if row.get("section") == "'Net Change in Cash'")
			opening = next(row for row in rows if row.get("section") == "Opening")
			closing = next(row for row in rows if row.get("section") == "Closing (Opening + Total)")
			period_keys = [column["fieldname"] for column in columns if column["fieldtype"] == "Currency"]
			return card, net_change["total"], [row[key] for row in (opening, closing) for key in period_keys]

		before_card, before_total, before_balances = report_values()
		for posting_date in (previous_year_start_date, year_start_date):
			make_journal_entry(
				"Office Equipments - _TC", "Cash - _TC", 500, posting_date=posting_date, submit=True
			)
			make_journal_entry("Cash - _TC", "Sales - _TC", 300, posting_date=posting_date, submit=True)

		card, total, balances = report_values()
		self.assertEqual(card - before_card, -1000)
		self.assertEqual(total - before_total, -400)
		self.assertEqual(
			[round(after - before, 2) for after, before in zip(balances, before_balances, strict=True)],
			[0] * 4 + [-200] * 4 + [-200] * 4 + [-400] * 4,
		)

	def test_net_change_in_cash_equals_cash_ledger_movement(self):
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
			accumulated_values=0,
		)

		def report_totals():
			rows = execute(filters)[1]
			return {row["section"]: row.get("total", 0) for row in rows if row.get("section")}

		before = report_totals()
		make_journal_entry("Cash - _TC", "Secured Loans - _TC", 1000, posting_date=today(), submit=True)
		sale = make_journal_entry("Cash - _TC", "Sales - _TC", 1180, posting_date=today(), save=False)
		sale.accounts[1].credit_in_account_currency = 1000
		sale.append(
			"accounts",
			{
				"account": "_Test Account VAT - _TC",
				"cost_center": "_Test Cost Center - _TC",
				"credit_in_account_currency": 180,
			},
		)
		sale.submit()
		depreciation = make_journal_entry(
			"_Test Depreciations - _TC",
			"_Test Accumulated Depreciations - _TC",
			100,
			posting_date=today(),
			save=False,
		)
		depreciation.voucher_type = "Depreciation Entry"
		depreciation.submit()
		after = report_totals()

		changes = {section: after[section] - before.get(section, 0) for section in after}
		self.assertEqual(changes["'Net Change in Cash'"], 2180)
		self.assertEqual(changes["Net Change in Other Balance Sheet Accounts"], 1180)
		self.assertEqual(changes["Depreciation"], 100)
		for label in ("Net Change in Accounts Receivable", "Net Change in Accounts Payable"):
			self.assertEqual(changes[label], 0)
