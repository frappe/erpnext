# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, flt, getdate, today

from erpnext.accounts.report import utils as report_utils
from erpnext.accounts.report.consolidated_financial_statement.consolidated_financial_statement import (
	CurrencyTranslator,
	execute,
	get_subsidiary_companies,
	prepare_companywise_opening_balance,
)
from erpnext.accounts.report.consolidated_trial_balance import consolidated_trial_balance
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
		self, debit_account, credit_account, amount, company=CHILD_COMPANY, posting_date=None, **party
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
		reporting_amount = frappe.db.get_value(
			"GL Entry", {"account": account.name}, "credit_in_reporting_currency"
		)
		self.assertEqual(flt(row.get(FOREIGN_CHILD_COMPANY)), 100)
		self.assertAlmostEqual(flt(row.get(PARENT_COMPANY)), flt(reporting_amount, 3))

	def test_cash_flow_accumulates_working_capital_into_group(self):
		filters = {"report": "Cash Flow", "accumulated_in_group_company": 1}
		before = self.run_report(**filters)
		self.post_credit_sales()
		after = self.run_report(**filters)

		profit_change = self.get_change(before, after, "Profit for the year")
		receivable_change = self.get_change(before, after, "Net Change in Accounts Receivable")
		translation_change = self.get_change(before, after, "Foreign Currency Translation Reserve")
		self.assertGreater(profit_change, 100)
		self.assertAlmostEqual(receivable_change, -(profit_change + translation_change), 2)
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
		after_row = self.get_row(after, account_name) or {}
		return flt(after_row.get(company)) - flt(before_row.get(company))

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

	def test_income_is_translated_at_the_transaction_rate(self):
		self.set_closing_rate(70)
		filters = {"report": "Profit and Loss Statement", "accumulated_in_group_company": 1}
		before = self.run_report(**filters)
		journal_entry = self.post_journal_entry(
			"Cash - CCU", "Sales - CCU", 100, company=FOREIGN_CHILD_COMPANY
		)
		after = self.run_report(**filters)

		transaction_rate = frappe.db.get_value(
			"GL Entry", {"voucher_no": journal_entry.name}, "reporting_currency_exchange_rate"
		)
		self.assertNotEqual(transaction_rate, 70)
		self.assertAlmostEqual(self.get_change(before, after, "Sales"), 100 * transaction_rate, 2)
		self.assertAlmostEqual(
			flt(self.get_row(after, "Sales", last_match=True)[PARENT_COMPANY]),
			self.get_trial_balance_sales(),
			2,
		)

		frappe.db.set_value(
			"GL Entry",
			{"voucher_no": journal_entry.name},
			{"debit_in_reporting_currency": 0, "credit_in_reporting_currency": 0},
		)
		without_reporting_amounts = self.run_report(**filters)
		self.assertAlmostEqual(
			self.get_change(before, without_reporting_amounts, "Sales"), 100 * transaction_rate, 2
		)

	def test_balance_sheet_shows_translation_reserve(self):
		self.set_closing_rate(70)
		filters = {"report": "Balance Sheet", "accumulated_in_group_company": 1}
		before = self.run_report(**filters)
		journal_entry = self.post_journal_entry(
			"Cash - CCU", "Sales - CCU", 100, company=FOREIGN_CHILD_COMPANY
		)
		after = self.run_report(**filters)

		transaction_rate = frappe.db.get_value(
			"GL Entry", {"voucher_no": journal_entry.name}, "reporting_currency_exchange_rate"
		)
		changes = {
			label: self.get_change(before, after, label)
			for label in (
				"Total Asset (Debit)",
				"Foreign Currency Translation Reserve",
				"Provisional Profit / Loss (Credit)",
				"Total (Credit)",
			)
		}
		self.assertAlmostEqual(changes["Total Asset (Debit)"], 100 * 70, 2)
		self.assertAlmostEqual(changes["Provisional Profit / Loss (Credit)"], 100 * transaction_rate, 2)
		self.assertAlmostEqual(
			changes["Foreign Currency Translation Reserve"], 100 * (70 - transaction_rate), 2
		)
		self.assertAlmostEqual(changes["Total (Credit)"], changes["Total Asset (Debit)"], 2)

	def test_balance_sheet_reserve_with_entries_without_reporting_amounts(self):
		self.set_closing_rate(70)
		filters = {"report": "Balance Sheet", "accumulated_in_group_company": 1}
		before = self.run_report(**filters)
		self.post_journal_entry("Cash - CCU", "Sales - CCU", 100, company=FOREIGN_CHILD_COMPANY)
		older_entry = self.post_journal_entry("Cash - CCU", "Sales - CCU", 50, company=FOREIGN_CHILD_COMPANY)
		frappe.db.set_value(
			"GL Entry",
			{"voucher_no": older_entry.name},
			{"debit_in_reporting_currency": 0, "credit_in_reporting_currency": 0},
		)
		after = self.run_report(**filters)

		transaction_rate = frappe.db.get_value(
			"GL Entry", {"voucher_no": older_entry.name}, "reporting_currency_exchange_rate"
		)
		profit_change = self.get_change(before, after, "Provisional Profit / Loss (Credit)")
		self.assertAlmostEqual(profit_change, 150 * transaction_rate, 2)

	def test_closed_year_leaves_no_provisional_profit(self):
		self.set_closing_rate(70)
		year_start_date = frappe.db.get_value("Fiscal Year", self.fiscal_year, "year_start_date")
		self.set_exchange_rate(60, year_start_date)
		filters = {"report": "Balance Sheet", "accumulated_in_group_company": 1}
		before = self.run_report(**filters)
		self.post_journal_entry(
			"Cash - CCU", "Sales - CCU", 100, company=FOREIGN_CHILD_COMPANY, posting_date=year_start_date
		)
		closing_voucher = self.close_period(FOREIGN_CHILD_COMPANY, year_start_date, today())
		after = self.run_report(**filters)

		closing_rate_of_voucher = frappe.db.get_value(
			"GL Entry", {"voucher_no": closing_voucher.name}, "reporting_currency_exchange_rate"
		)
		self.assertAlmostEqual(self.get_change(before, after, "Provisional Profit / Loss (Credit)"), 0, 2)
		self.assertAlmostEqual(
			self.get_change(before, after, "Foreign Currency Translation Reserve"),
			100 * (70 - closing_rate_of_voucher),
			2,
		)

		closing_voucher.db_set("gle_processing_status", "In Progress")
		fiscal_year = frappe._dict(
			frappe.db.get_value(
				"Fiscal Year", self.fiscal_year, ["year_start_date", "year_end_date"], as_dict=True
			)
		)
		translator = CurrencyTranslator({}, frappe._dict(filter_based_on="Fiscal Year"), fiscal_year)
		self.assertEqual(translator.get_unclosed_from_date(FOREIGN_CHILD_COMPANY), getdate(year_start_date))

	def close_period(self, company, period_start_date, period_end_date):
		closing_voucher = frappe.get_doc(
			{
				"doctype": "Period Closing Voucher",
				"transaction_date": period_end_date,
				"period_start_date": period_start_date,
				"period_end_date": period_end_date,
				"company": company,
				"fiscal_year": self.fiscal_year,
				"cost_center": frappe.get_cached_value("Company", company, "cost_center"),
				"closing_account_head": frappe.db.get_value(
					"Account", {"company": company, "root_type": "Equity", "is_group": 0}
				),
				"remarks": "test",
			}
		)
		closing_voucher.submit()
		return closing_voucher

	def set_closing_rate(self, rate):
		year_end_date = frappe.db.get_value("Fiscal Year", self.fiscal_year, "year_end_date")
		self.set_exchange_rate(rate, year_end_date)

	def set_exchange_rate(self, rate, date):
		for from_currency, to_currency, exchange_rate in (("USD", "INR", rate), ("INR", "USD", 1 / rate)):
			frappe.get_doc(
				{
					"doctype": "Currency Exchange",
					"date": date,
					"from_currency": from_currency,
					"to_currency": to_currency,
					"exchange_rate": exchange_rate,
				}
			).insert()

		vars(report_utils)["__exchange_rates"].clear()
		self.addCleanup(vars(report_utils)["__exchange_rates"].clear)

	def get_trial_balance_sales(self):
		filters = frappe._dict({"company": [PARENT_COMPANY], "fiscal_year": self.fiscal_year})
		data = consolidated_trial_balance.execute(filters)[1]
		row = next(row for row in data if row.get("account_name") == "Sales")
		return flt(row["closing_credit"]) - flt(row["closing_debit"])
