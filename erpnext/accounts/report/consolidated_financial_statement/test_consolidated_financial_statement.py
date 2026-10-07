# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.utils import add_days, flt, today

from erpnext.accounts.report.consolidated_financial_statement.consolidated_financial_statement import (
	execute,
	get_subsidiary_companies,
	prepare_companywise_opening_balance,
)
from erpnext.accounts.report.utils import convert
from erpnext.accounts.utils import get_fiscal_year
from erpnext.tests.utils import ERPNextTestSuite

PARENT_COMPANY = "Parent Group Company India"
CHILD_COMPANY = "Child Company India"
FOREIGN_CHILD_COMPANY = "Child Company US"


class TestConsolidatedFinancialStatement(ERPNextTestSuite):
	"""Consolidation is exercised via the bootstrap group of companies
	(`Parent Group Company India` with child `Child Company India`). Income and
	expense posted in the child company must surface in the report that is run
	for the parent (group) company."""

	def setUp(self):
		self.fiscal_year = get_fiscal_year(today(), company=PARENT_COMPANY)[0]

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

	def post_journal_entry(
		self, debit_account, credit_account, amount, posting_date=None, company=CHILD_COMPANY, **party
	):
		je = frappe.new_doc("Journal Entry")
		je.posting_date = posting_date or today()
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
		"""Return the first (or last) row whose account_name contains the fragment.

		Pass ``last_match=True`` to get the leaf/most-specific match when the fragment
		is also a prefix of a parent group account (parents precede children in tree order).
		"""
		found = None
		for row in data:
			if account_name_fragment in str(row.get("account_name") or ""):
				if not last_match:
					return row
				found = row
		return found

	def test_profit_and_loss_reflects_child_company_income(self):
		amount = 7000
		self.post_journal_entry("Cash - CCI", "Sales - CCI", amount)

		data = self.run_report(report="Profit and Loss Statement", accumulated_in_group_company=0)

		self.assertTrue(data, "Report returned no rows")

		# child's Sales account is mapped onto the parent chart (Sales - PGCI)
		sales_row = self.get_row(data, "Sales", last_match=True)
		self.assertIsNotNone(sales_row, "Sales row missing from consolidated P&L")
		# >= so a pre-existing Sales balance in the fiscal year doesn't make this brittle
		self.assertGreaterEqual(flt(sales_row.get(CHILD_COMPANY)), amount)

		total_income_row = self.get_row(data, "Total Income (Credit)")
		self.assertIsNotNone(total_income_row, "Total Income row missing")
		self.assertGreaterEqual(flt(total_income_row.get("total")), amount)

	def test_profit_and_loss_reflects_child_company_expense(self):
		amount = 3000
		self.post_journal_entry("Marketing Expenses - CCI", "Cash - CCI", amount)

		data = self.run_report(report="Profit and Loss Statement", accumulated_in_group_company=0)

		expense_row = self.get_row(data, "Marketing Expenses", last_match=True)
		self.assertIsNotNone(expense_row, "Marketing Expenses row missing from consolidated P&L")
		self.assertGreaterEqual(flt(expense_row.get(CHILD_COMPANY)), amount)

		total_expense_row = self.get_row(data, "Total Expense (Debit)")
		self.assertIsNotNone(total_expense_row, "Total Expense row missing")
		self.assertGreaterEqual(flt(total_expense_row.get("total")), amount)

	def test_accumulated_in_group_company_rolls_up_to_parent(self):
		"""With `accumulated_in_group_company`, the child's amount is also
		accumulated into the parent company column."""
		amount = 5000
		self.post_journal_entry("Cash - CCI", "Sales - CCI", amount)

		data = self.run_report(report="Profit and Loss Statement", accumulated_in_group_company=1)

		sales_row = self.get_row(data, "Sales", last_match=True)
		self.assertIsNotNone(sales_row)
		child_value = flt(sales_row.get(CHILD_COMPANY))
		self.assertGreaterEqual(child_value, amount)
		# parent column picks up the child value when accumulated
		self.assertEqual(flt(sales_row.get(PARENT_COMPANY)), child_value)
		# the total equals the consolidated (group) value, not the sum of parent + child
		# columns -- this is the regression guard for the double-count fix
		self.assertEqual(flt(sales_row.get("total")), child_value)

	def test_balance_sheet_executes_and_returns_rows(self):
		# posting income leaves a balancing entry in the child's Cash (Asset) account
		amount = 4000
		self.post_journal_entry("Cash - CCI", "Sales - CCI", amount)

		data = self.run_report(report="Balance Sheet", accumulated_in_group_company=0)

		self.assertTrue(data, "Balance Sheet returned no rows")
		cash_row = self.get_row(data, "Cash")
		self.assertIsNotNone(cash_row, "Cash asset row missing from consolidated Balance Sheet")
		self.assertGreaterEqual(flt(cash_row.get(CHILD_COMPANY)), amount)

	def test_accumulated_profit_total_is_the_group_company_value(self):
		self.post_journal_entry("Cash - CCI", "Sales - CCI", 5000)

		data = self.run_report(report="Profit and Loss Statement", accumulated_in_group_company=1)

		profit_row = self.get_row(data, "Profit for the year")
		total_income_row = self.get_row(data, "Total Income (Credit)")
		total_expense_row = self.get_row(data, "Total Expense (Debit)") or {}
		self.assertEqual(flt(profit_row["total"]), flt(profit_row[PARENT_COMPANY]))
		self.assertEqual(
			flt(profit_row["total"]), flt(total_income_row["total"]) - flt(total_expense_row.get("total"))
		)

	def test_accumulated_balance_sheet_profit_totals_are_the_group_company_value(self):
		self.post_journal_entry("Cash - CCI", "Sales - CCI", 4000)

		data = self.run_report(report="Balance Sheet", accumulated_in_group_company=1)

		for label in ("Provisional Profit / Loss (Credit)", "Total (Credit)"):
			row = self.get_row(data, label)
			self.assertEqual(flt(row["total"]), flt(row[PARENT_COMPANY]), label)

	def test_unclosed_fiscal_years_total_covers_every_company(self):
		year_start_date = get_fiscal_year(today(), company=PARENT_COMPANY)[1]
		self.post_journal_entry("Cash - CCI", "Sales - CCI", 6000, posting_date=add_days(year_start_date, -1))

		data = self.run_report(report="Balance Sheet", accumulated_in_group_company=0)
		row = self.get_row(data, "Unclosed Fiscal Years")
		companies_total = sum(flt(row[company]) for company in get_subsidiary_companies(PARENT_COMPANY))
		self.assertEqual(flt(row["total"]), companies_total)

		data = self.run_report(report="Balance Sheet", accumulated_in_group_company=1)
		row = self.get_row(data, "Unclosed Fiscal Years")
		self.assertEqual(flt(row["total"]), flt(row[PARENT_COMPANY]))

	def test_accumulated_cash_flow_section_total_is_under_the_group_company(self):
		self.post_journal_entry("Cash - CCI", "Sales - CCI", 5000)

		data = self.run_report(report="Cash Flow", accumulated_in_group_company=1)

		operations_header = data[0]["account"]
		section_rows = [row for row in data if row.get("parent_account") == operations_header]
		section_total = self.get_row(data, "Net Cash from Operations")
		self.assertEqual(
			flt(section_total.get(PARENT_COMPANY)), sum(flt(row.get(PARENT_COMPANY)) for row in section_rows)
		)

	def test_accumulated_cash_flow_rows_include_subsidiaries(self):
		self.post_journal_entry("Office Equipment - CCI", "Cash - CCI", 3000)

		own_row = self.get_row(
			self.run_report(report="Cash Flow", accumulated_in_group_company=0), "Net Change in Fixed Asset"
		)
		accumulated_row = self.get_row(
			self.run_report(report="Cash Flow", accumulated_in_group_company=1), "Net Change in Fixed Asset"
		)
		self.assertEqual(flt(own_row[CHILD_COMPANY]), -3000)
		self.assertEqual(
			flt(accumulated_row[PARENT_COMPANY]), flt(own_row[PARENT_COMPANY]) + flt(own_row[CHILD_COMPANY])
		)

	def test_accumulated_cash_flow_row_total_is_the_group_company_value(self):
		frappe.get_doc(
			doctype="Currency Exchange",
			date=get_fiscal_year(today(), company=PARENT_COMPANY)[1],
			from_currency="USD",
			to_currency="INR",
			exchange_rate=80,
			for_buying=1,
			for_selling=1,
		).insert()
		self.post_journal_entry("Office Equipment - CCU", "Cash - CCU", 100, company="Child Company US")

		with patch("erpnext.accounts.report.utils.get_rate_as_at", return_value=0.0125):
			data = self.run_report(report="Cash Flow", accumulated_in_group_company=1)

		row = self.get_row(data, "Net Change in Fixed Asset")
		self.assertEqual(flt(row["total"]), flt(row[PARENT_COMPANY]))

	def test_accumulated_column_uses_its_own_company_currency(self):
		intermediate_company = "_Test Company 7"
		child_company = frappe.get_doc("Company", "Best Test")
		child_company.parent_company = intermediate_company
		child_company.save()
		self.post_journal_entry("Cash - BT", "Sales - BT", 8000, company=child_company.name)

		filters = {"company": "_Test Company 6", "report": "Profit and Loss Statement"}
		with patch(
			"erpnext.accounts.report.utils.get_rate_as_at",
			side_effect=lambda date, from_, to: {("USD", "INR"): 80, ("INR", "USD"): 0.0125}.get((from_, to)),
		):
			own_data = self.run_report(**filters, accumulated_in_group_company=0)
			accumulated_data = self.run_report(**filters, accumulated_in_group_company=1)

		own_row = self.get_row(own_data, "Profit for the year")
		accumulated_row = self.get_row(accumulated_data, "Profit for the year")
		self.assertAlmostEqual(
			flt(accumulated_row[intermediate_company]),
			flt(own_row.get(intermediate_company)) + flt(own_row[child_company.name]) * 0.0125,
			places=2,
		)

	def test_child_only_account_of_foreign_child_is_converted(self):
		account = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "_Test Consolidated Consulting",
				"parent_account": "Direct Income - CCU",
				"company": FOREIGN_CHILD_COMPANY,
			}
		)
		account.flags.ignore_root_company_validation = True
		account.insert()
		self.post_journal_entry("Cash - CCU", account.name, 100, company=FOREIGN_CHILD_COMPANY)

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
		self.post_journal_entry("Cash - CCI", "Sales - CCI", 100)
		after = self.run_report(**filters)
		summary_after = self.get_summary_value("Net Change in Cash", **filters)

		for label in ("Net Cash from Operations", "Net Change in Cash"):
			for company in (PARENT_COMPANY, CHILD_COMPANY):
				self.assertAlmostEqual(self.get_change(before, after, label, company), 100, 2)
		self.assertAlmostEqual(summary_after - summary_before, 100, 2)

	def post_credit_sales(self):
		self.post_journal_entry(
			"Debtors - CCI", "Sales - CCI", 100, party_type="Customer", party="_Test Customer"
		)
		self.post_journal_entry(
			"Debtors - CCU",
			"Sales - CCU",
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
		self.post_journal_entry("Cash - CCU", "Sales - CCU", 100, company=FOREIGN_CHILD_COMPANY)
		after = self.get_summary_value("Total Income", **filters)

		self.assertEqual(after, before)

	def get_summary_value(self, label, **extra):
		summary = self.execute_report(**extra)[4]
		return next(flt(card["value"]) for card in summary if card["label"] == label)

	def test_unclosed_year_message_only_with_opening_balance(self):
		companies = [PARENT_COMPANY, CHILD_COMPANY]
		asset_root = frappe._dict(
			root_type="Asset", account_name="Application of Funds (Assets)", company_wise_opening_bal={}
		)

		self.assertEqual(prepare_companywise_opening_balance([asset_root], [], [], companies), ("", {}))

		asset_root.company_wise_opening_bal = {CHILD_COMPANY: 500}
		message, opening_balance = prepare_companywise_opening_balance([asset_root], [], [], companies)
		self.assertTrue(message)
		self.assertEqual(opening_balance[CHILD_COMPANY], 500)
