# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import flt, today

from erpnext.accounts.report.consolidated_financial_statement.consolidated_financial_statement import (
	execute,
)
from erpnext.accounts.utils import get_fiscal_year
from erpnext.tests.utils import ERPNextTestSuite

PARENT_COMPANY = "Parent Group Company India"
CHILD_COMPANY = "Child Company India"


class TestConsolidatedFinancialStatement(ERPNextTestSuite):
	"""Consolidation is exercised via the bootstrap group of companies
	(`Parent Group Company India` with child `Child Company India`). Income and
	expense posted in the child company must surface in the report that is run
	for the parent (group) company."""

	def setUp(self):
		self.fiscal_year = get_fiscal_year(today(), company=PARENT_COMPANY)[0]

	def run_report(self, **extra):
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
		return execute(filters)[1]

	def post_journal_entry(self, debit_account, credit_account, amount, company=CHILD_COMPANY):
		je = frappe.new_doc("Journal Entry")
		je.posting_date = today()
		je.company = company
		je.set(
			"accounts",
			[
				{"account": debit_account, "debit_in_account_currency": amount},
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
		year_start_date = get_fiscal_year(today(), company=PARENT_COMPANY)[1]
		for from_currency, to_currency, exchange_rate in (("USD", "INR", 80), ("INR", "USD", 0.0125)):
			frappe.get_doc(
				doctype="Currency Exchange",
				date=year_start_date,
				from_currency=from_currency,
				to_currency=to_currency,
				exchange_rate=exchange_rate,
				for_buying=1,
				for_selling=1,
			).insert()
		self.post_journal_entry("Office Equipment - CCU", "Cash - CCU", 100, company="Child Company US")

		data = self.run_report(report="Cash Flow", accumulated_in_group_company=1)

		row = self.get_row(data, "Net Change in Fixed Asset")
		self.assertEqual(flt(row["total"]), flt(row[PARENT_COMPANY]))
