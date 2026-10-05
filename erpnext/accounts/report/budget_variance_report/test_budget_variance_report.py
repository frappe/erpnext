# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import nowdate

from erpnext.accounts.doctype.budget.test_budget import make_budget, set_total_expense_zero
from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.report.budget_variance_report.budget_variance_report import execute
from erpnext.accounts.utils import get_fiscal_year
from erpnext.tests.utils import ERPNextTestSuite

ACCOUNT = "_Test Account Cost for Goods Sold - _TC"
COST_CENTER = "_Test Cost Center - _TC"
COST_CENTER_2 = "_Test Cost Center 2 - _TC"
PAST_FISCAL_YEAR = "_Test Fiscal Year 2025"


class TestBudgetVarianceReport(ERPNextTestSuite):
	def setUp(self):
		self.fy = get_fiscal_year(nowdate())[0]

	def run_report(self, **extra):
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"from_fiscal_year": self.fy,
				"to_fiscal_year": self.fy,
				"period": "Yearly",
				"budget_against": "Cost Center",
				**extra,
			}
		)
		return execute(filters)[1]

	def report_row(self, data, dimension, account=ACCOUNT):
		row = next(
			(r for r in data if r["budget_against"] == dimension and r["account"] == account),
			None,
		)
		self.assertIsNotNone(row, f"No report row for {dimension} / {account}")
		return row

	def field(self, label):
		return frappe.scrub(f"{label} {self.fy}")

	def test_report_executes(self):
		# Smoke-guards the raw-SQL -> query-builder port: the report query must compile and run on
		# both MariaDB and postgres.
		columns, *_rest = execute(
			frappe._dict(
				{
					"company": "_Test Company",
					"from_fiscal_year": self.fy,
					"to_fiscal_year": self.fy,
					"period": "Yearly",
					"budget_against": "Cost Center",
				}
			)
		)
		self.assertTrue(columns)

	def test_budget_amount_shown_with_zero_actual(self):
		# neutralise any committed actuals so the exact Actual/Variance assertions hold
		set_total_expense_zero(nowdate(), "cost_center")
		make_budget(
			budget_against="Cost Center", cost_center=COST_CENTER, budget_amount=120000, submit_budget=1
		)

		row = self.report_row(self.run_report(), COST_CENTER)
		self.assertEqual(row[self.field("Budget")], 120000)
		self.assertEqual(row[self.field("Actual")], 0)
		self.assertEqual(row[self.field("Variance")], 120000)

	def test_actual_expense_updates_actual_and_variance(self):
		# zero out pre-committed actuals: keeps Actual exact and avoids the budget's
		# "Stop" action rejecting the journal entry when prior actuals already exist
		set_total_expense_zero(nowdate(), "cost_center")
		make_budget(
			budget_against="Cost Center", cost_center=COST_CENTER, budget_amount=120000, submit_budget=1
		)
		# book an actual expense well within the annual budget so the "Stop" action does not block it
		make_journal_entry(ACCOUNT, "_Test Bank - _TC", 50000, cost_center=COST_CENTER, submit=True)

		row = self.report_row(self.run_report(), COST_CENTER)
		self.assertEqual(row[self.field("Actual")], 50000)
		self.assertEqual(row[self.field("Variance")], 70000)  # 120000 - 50000

	def test_budget_against_filter_limits_dimensions(self):
		make_budget(
			budget_against="Cost Center", cost_center=COST_CENTER, budget_amount=120000, submit_budget=1
		)
		make_budget(
			budget_against="Cost Center", cost_center=COST_CENTER_2, budget_amount=80000, submit_budget=1
		)

		data = self.run_report(budget_against_filter=[COST_CENTER])
		dimensions = {row["budget_against"] for row in data}
		self.assertEqual(dimensions, {COST_CENTER})

	def test_monthly_period_totals(self):
		# zero out pre-committed actuals so total_actual reflects only this test's entry
		set_total_expense_zero(nowdate(), "cost_center")
		make_budget(
			budget_against="Cost Center", cost_center=COST_CENTER, budget_amount=120000, submit_budget=1
		)
		make_journal_entry(ACCOUNT, "_Test Bank - _TC", 50000, cost_center=COST_CENTER, submit=True)

		row = self.report_row(self.run_report(period="Monthly"), COST_CENTER)
		# totals roll up the per-month columns across the year
		self.assertEqual(row["total_budget"], 120000)
		self.assertEqual(row["total_actual"], 50000)
		self.assertEqual(row["total_variance"], 70000)

	def test_no_budget_returns_no_rows(self):
		# a dimension without any budget produces no report rows
		data = self.run_report(budget_against_filter=["_Test Write Off Cost Center - _TC"])
		self.assertEqual(data, [])

	def test_period_closing_entries_are_not_actuals(self):
		self.fy = PAST_FISCAL_YEAR
		make_past_budget(COST_CENTER)
		make_journal_entry(
			ACCOUNT, "_Test Bank - _TC", 5000, cost_center=COST_CENTER, posting_date="2025-05-10", submit=True
		)
		actual = self.report_row(self.run_report(), COST_CENTER)[self.field("Actual")]

		closing = make_journal_entry(
			"_Test Bank - _TC",
			ACCOUNT,
			actual,
			cost_center=COST_CENTER,
			posting_date="2025-12-31",
			submit=True,
		)
		gl_entry = frappe.qb.DocType("GL Entry")
		frappe.qb.update(gl_entry).set(gl_entry.voucher_type, "Period Closing Voucher").where(
			gl_entry.voucher_no == closing.name
		).run()

		self.assertEqual(self.report_row(self.run_report(), COST_CENTER)[self.field("Actual")], actual)

	def test_entries_of_other_finance_books_are_not_actuals(self):
		self.fy = PAST_FISCAL_YEAR
		make_past_budget(COST_CENTER)
		actual = self.report_row(self.run_report(), COST_CENTER)[self.field("Actual")]

		journal_entry = make_journal_entry(
			ACCOUNT, "_Test Bank - _TC", 7000, cost_center=COST_CENTER, posting_date="2025-05-10", save=False
		)
		journal_entry.finance_book = make_finance_book()
		journal_entry.submit()

		self.assertEqual(self.report_row(self.run_report(), COST_CENTER)[self.field("Actual")], actual)


def make_finance_book():
	finance_book = "_Test Budget Variance Finance Book"
	if not frappe.db.exists("Finance Book", finance_book):
		frappe.get_doc({"doctype": "Finance Book", "finance_book_name": finance_book}).insert()
	return finance_book


def make_past_budget(cost_center):
	return make_budget(
		budget_against="Cost Center",
		cost_center=cost_center,
		budget_amount=10000000,
		from_fiscal_year=PAST_FISCAL_YEAR,
		to_fiscal_year=PAST_FISCAL_YEAR,
		submit_budget=1,
	)
