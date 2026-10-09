# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import os
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

	def ifrs_template_totals(self, *lines):
		"""Run the shipped IFRS cash flow template for the current fiscal year and return the given lines."""
		fiscal_year, year_start_date, year_end_date = get_fiscal_year(today(), company=self.company)
		filters = frappe._dict(
			company=self.company,
			report_template=self.shipped_ifrs_template(),
			from_fiscal_year=fiscal_year,
			to_fiscal_year=fiscal_year,
			period_start_date=year_start_date,
			period_end_date=year_end_date,
			filter_based_on="Fiscal Year",
			periodicity="Yearly",
			accumulated_values=0,
		)
		rows = execute(filters)[1]
		return [next(row for row in rows if row.get("account") == line)["total"] for line in lines]

	def shipped_ifrs_template(self):
		"""Insert a copy of the template file, since sites keep the copy synced when they were set up."""
		name = "_Test Standard Cash Flow Statement (IFRS)"
		if frappe.db.exists("Financial Report Template", name):
			return name

		template_path = frappe.get_module_path(
			"Accounts", "financial_report_template", "standard_cash_flow_statement_(ifrs)"
		)
		with open(os.path.join(template_path, "standard_cash_flow_statement_(ifrs).json")) as template_file:
			template = frappe.parse_json(template_file.read())

		template.update(name=None, template_name=name, module=None)
		return frappe.get_doc(template).insert().name

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

	def test_ifrs_template_counts_short_term_borrowings_once(self):
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry

		overdraft_account = frappe.get_doc(
			doctype="Account",
			account_name="_Test Bank Overdraft",
			parent_account="Current Liabilities - _TC",
			company=self.company,
			account_category="Short-term Borrowings",
		).insert()
		lines = (
			"Increase/(decrease) in other current liabilities",
			"Proceeds from / Repayment of borrowings",
			"NET INCREASE/(DECREASE) IN CASH AND CASH EQUIVALENTS",
		)

		before = self.ifrs_template_totals(*lines)
		make_journal_entry("Cash - _TC", overdraft_account.name, 1000, posting_date=today(), submit=True)
		after = self.ifrs_template_totals(*lines)

		self.assertEqual([a - b for a, b in zip(after, before, strict=True)], [0, 1000, 1000])

	def test_ifrs_template_profit_before_tax_includes_accounts_without_category(self):
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry

		expense_account = frappe.get_doc(
			doctype="Account",
			account_name="_Test Uncategorised Fees",
			parent_account="Indirect Expenses - _TC",
			company=self.company,
		).insert()
		lines = ("Profit before tax", "NET INCREASE/(DECREASE) IN CASH AND CASH EQUIVALENTS")

		before = self.ifrs_template_totals(*lines)
		make_journal_entry(expense_account.name, "Cash - _TC", 100, posting_date=today(), submit=True)
		after = self.ifrs_template_totals(*lines)

		self.assertEqual([a - b for a, b in zip(after, before, strict=True)], [-100, -100])

	def test_patch_fixes_only_unchanged_ifrs_formulas(self):
		from erpnext.accounts.doctype.financial_report_template.financial_report_template import (
			sync_financial_report_templates,
		)
		from erpnext.patches.v16_0.fix_ifrs_cash_flow_template_formulas import FORMULAS, TEMPLATE, execute

		sync_financial_report_templates()
		rows = {
			code: frappe.db.get_value(
				"Financial Report Row", {"parent": TEMPLATE, "reference_code": code}, "name"
			)
			for code in FORMULAS
		}
		custom_formula = '["account_category", "in", ["Other Payables"]]'
		frappe.db.set_value(
			"Financial Report Row", rows["CF_OP100"], "calculation_formula", FORMULAS["CF_OP100"][0]
		)
		frappe.db.set_value("Financial Report Row", rows["CF_WC500"], "calculation_formula", custom_formula)

		execute()

		self.assertEqual(
			frappe.db.get_value("Financial Report Row", rows["CF_OP100"], "calculation_formula"),
			FORMULAS["CF_OP100"][1],
		)
		self.assertEqual(
			frappe.db.get_value("Financial Report Row", rows["CF_WC500"], "calculation_formula"),
			custom_formula,
		)

	def test_patch_keeps_borrowings_when_financing_row_was_changed(self):
		from erpnext.accounts.doctype.financial_report_template.financial_report_template import (
			sync_financial_report_templates,
		)
		from erpnext.patches.v16_0.fix_ifrs_cash_flow_template_formulas import FORMULAS, TEMPLATE, execute

		sync_financial_report_templates()

		def row(code):
			return frappe.db.get_value(
				"Financial Report Row", {"parent": TEMPLATE, "reference_code": code}, "name"
			)

		frappe.db.set_value(
			"Financial Report Row",
			row("CF_FIN200"),
			"calculation_formula",
			'["account_category", "in", ["Long-term Borrowings"]]',
		)
		frappe.db.set_value(
			"Financial Report Row", row("CF_WC500"), "calculation_formula", FORMULAS["CF_WC500"][0]
		)

		execute()

		self.assertEqual(
			frappe.db.get_value("Financial Report Row", row("CF_WC500"), "calculation_formula"),
			FORMULAS["CF_WC500"][0],
		)
