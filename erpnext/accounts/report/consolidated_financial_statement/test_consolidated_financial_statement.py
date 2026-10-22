# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, flt, today

from erpnext.accounts.report.consolidated_financial_statement.consolidated_financial_statement import (
	execute,
)
from erpnext.accounts.report.utils import convert
from erpnext.accounts.utils import get_fiscal_year

PARENT_COMPANY = "_Test Consolidation Parent"
CHILD_COMPANY = "_Test Consolidation Child"
FOREIGN_CHILD_COMPANY = "_Test Consolidation Child US"
CHILD_ABBR, FOREIGN_CHILD_ABBR = "_TCCI", "_TCCU"

test_dependencies = ["Customer", "Currency Exchange"]


class TestConsolidatedFinancialStatement(FrappeTestCase):
	"""A group company with an INR and a USD child company."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_company(PARENT_COMPANY, "_TCCP", "INR", "India", is_group=1)
		make_company(CHILD_COMPANY, CHILD_ABBR, "INR", "India", parent_company=PARENT_COMPANY)
		make_company(
			FOREIGN_CHILD_COMPANY, FOREIGN_CHILD_ABBR, "USD", "United States", parent_company=PARENT_COMPANY
		)

	def setUp(self):
		self.fiscal_year = get_fiscal_year(today(), company=PARENT_COMPANY)[0]
		make_usd_inr_exchange_rates()

	def run_report(self, **extra):
		return self.execute_report(**extra)[1]

	def execute_report(self, **extra):
		filters = frappe._dict(
			{
				"company": PARENT_COMPANY,
				"filter_based_on": "Fiscal Year",
				"from_fiscal_year": self.fiscal_year,
				"to_fiscal_year": self.fiscal_year,
				"periodicity": "Yearly",
				"include_default_book_entries": 1,
			}
		)
		filters.update(extra)
		return execute(filters)

	def post_journal_entry(self, debit_account, credit_account, amount, company=CHILD_COMPANY, **party):
		je = frappe.new_doc("Journal Entry")
		je.posting_date = today()
		je.company = company
		je.set(
			"accounts",
			[
				{"account": debit_account, "debit_in_account_currency": amount, **party},
				{"account": credit_account, "credit_in_account_currency": amount},
			],
		)
		je.save()
		je.submit()
		return je

	def get_row(self, data, account_name_fragment, last_match=False):
		"""Return the first (or last) row whose account_name contains the fragment."""
		found = None
		for row in data:
			if account_name_fragment in str(row.get("account_name") or ""):
				if not last_match:
					return row
				found = row
		return found

	def test_child_only_account_of_foreign_child_is_converted(self):
		account = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "_Test Consolidated Consulting",
				"parent_account": "Direct Income - _TCCU",
				"company": FOREIGN_CHILD_COMPANY,
			}
		)
		account.flags.ignore_root_company_validation = True
		account.insert()
		self.post_journal_entry("Cash - _TCCU", account.name, 100, company=FOREIGN_CHILD_COMPANY)

		data = self.run_report(report="Profit and Loss Statement", accumulated_in_group_company=1)

		row = self.get_row(data, "_Test Consolidated Consulting")
		year_end_date = frappe.db.get_value("Fiscal Year", self.fiscal_year, "year_end_date")
		self.assertEqual(flt(row.get(FOREIGN_CHILD_COMPANY)), 100)
		self.assertAlmostEqual(
			flt(row.get(PARENT_COMPANY)), flt(convert(100, "INR", "USD", year_end_date), 3)
		)

	def test_cash_flow_accumulates_working_capital_into_group(self):
		filters = {"report": "Cash Flow", "accumulated_in_group_company": 1}
		before = self.run_report(**filters)
		self.post_credit_sales()
		after = self.run_report(**filters)

		profit_change = self.get_change(before, after, "Profit for the year")
		receivable_change = self.get_change(before, after, "Net Change in Accounts Receivable")
		self.assertGreater(profit_change, 100)
		self.assertAlmostEqual(receivable_change, -profit_change, 2)
		self.assertAlmostEqual(self.get_change(before, after, "Net Change in Cash"), 0, 2)

	def test_cash_flow_totals_fill_every_company_column(self):
		filters = {"report": "Cash Flow", "accumulated_in_group_company": 1}
		before = self.run_report(**filters)
		summary_before = self.get_summary_value("Net Change in Cash", **filters)
		self.post_journal_entry("Cash - _TCCI", "Sales - _TCCI", 100)
		after = self.run_report(**filters)
		summary_after = self.get_summary_value("Net Change in Cash", **filters)

		for label in ("Net Cash from Operations", "Net Change in Cash"):
			for company in (PARENT_COMPANY, CHILD_COMPANY):
				self.assertAlmostEqual(self.get_change(before, after, label, company), 100, 2)
		self.assertAlmostEqual(summary_after - summary_before, 100, 2)

	def post_credit_sales(self):
		self.post_journal_entry(
			"Debtors - _TCCI", "Sales - _TCCI", 100, party_type="Customer", party="_Test Customer"
		)
		self.post_journal_entry(
			"Debtors - _TCCU",
			"Sales - _TCCU",
			100,
			company=FOREIGN_CHILD_COMPANY,
			party_type="Customer",
			party="_Test Customer USD",
		)

	def get_change(self, before, after, account_name, company=PARENT_COMPANY):
		before_row = self.get_row(before, account_name) or {}
		return flt(self.get_row(after, account_name).get(company)) - flt(before_row.get(company))

	def test_cash_flow_converts_working_capital_to_presentation_currency(self):
		filters = {"report": "Cash Flow", "presentation_currency": "USD"}
		before = self.run_report(**filters)
		self.post_credit_sales()
		after = self.run_report(**filters)

		for company in (PARENT_COMPANY, CHILD_COMPANY, FOREIGN_CHILD_COMPANY):
			self.assertAlmostEqual(self.get_change(before, after, "Net Change in Cash", company), 0, 2)

	def test_cash_flow_working_capital_follows_date_range(self):
		year_end_date = frappe.db.get_value("Fiscal Year", self.fiscal_year, "year_end_date")
		filters = {
			"report": "Cash Flow",
			"filter_based_on": "Date Range",
			"period_start_date": add_days(today(), 1),
			"period_end_date": year_end_date,
		}
		before = self.run_report(**filters)
		self.post_credit_sales()
		after = self.run_report(**filters)

		change = self.get_change(before, after, "Net Change in Accounts Receivable", CHILD_COMPANY)
		self.assertEqual(change, 0)

	def test_summary_does_not_add_columns_in_different_currencies(self):
		filters = {"report": "Profit and Loss Statement", "accumulated_in_group_company": 0}
		before = self.get_summary_value("Total Income", **filters)
		self.post_journal_entry("Cash - _TCCU", "Sales - _TCCU", 100, company=FOREIGN_CHILD_COMPANY)
		after = self.get_summary_value("Total Income", **filters)

		self.assertEqual(after, before)

	def get_summary_value(self, label, **extra):
		summary = self.execute_report(**extra)[4]
		return next(flt(card["value"]) for card in summary if card["label"] == label)


def make_usd_inr_exchange_rates():
	"""Reports stop when a rate is missing, so the foreign child company needs today's USD<->INR rates."""
	from erpnext.accounts.report import utils as report_utils

	for from_currency, to_currency, exchange_rate in (("USD", "INR", 62.9), ("INR", "USD", 0.0167)):
		filters = {"date": today(), "from_currency": from_currency, "to_currency": to_currency}
		if not frappe.db.exists("Currency Exchange", filters):
			frappe.get_doc(doctype="Currency Exchange", exchange_rate=exchange_rate, **filters).insert()

	vars(report_utils)["__exchange_rates"].clear()


def make_company(name, abbr, currency, country, is_group=0, parent_company=None):
	if frappe.db.exists("Company", name):
		return

	frappe.get_doc(
		{
			"doctype": "Company",
			"company_name": name,
			"abbr": abbr,
			"default_currency": currency,
			"country": country,
			"is_group": is_group,
			"parent_company": parent_company,
			"create_chart_of_accounts_based_on": "Standard Template",
			"chart_of_accounts": "Standard",
		}
	).insert()
	# a child company copies the parent's chart, including the parent's account currency
	frappe.db.set_value("Account", {"company": name}, "account_currency", currency)
