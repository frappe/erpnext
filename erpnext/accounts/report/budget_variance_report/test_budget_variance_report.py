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


class TestBudgetVarianceReport(ERPNextTestSuite):
	def setUp(self):
		self.fy = get_fiscal_year(nowdate())[0]

	def run_report(self, return_full=False, **extra):
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
		result = execute(filters)
		return result if return_full else result[1]

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

	def test_chart_data_actual_aligned_with_correct_period(self):
		# guards against the chart plotting an actual amount under the previous
		# period's label instead of the period the transaction was actually posted in
		set_total_expense_zero(nowdate(), "cost_center")
		make_budget(
			budget_against="Cost Center", cost_center=COST_CENTER, budget_amount=120000, submit_budget=1
		)
		make_journal_entry(ACCOUNT, "_Test Bank - _TC", 50000, cost_center=COST_CENTER, submit=True)

		_columns, data, _, chart_data = self.run_report(period="Monthly", return_full=True)
		self.assertIsNotNone(chart_data)

		month_label = frappe.utils.formatdate(nowdate(), "MMM")
		target_label = f"({month_label}) {self.fy}"

		labels = chart_data["data"]["labels"]

		self.assertIn(target_label, labels)
		idx = labels.index(target_label)

		actual_values = next(
			d["values"] for d in chart_data["data"]["datasets"] if d["name"] == frappe._("Actual Expense")
		)

		self.assertEqual(len(labels), len(actual_values))

		# the journal entry's amount must land under its own posting month
		self.assertEqual(actual_values[idx], 50000)

		# and must not leak into any neighbouring period (the original bug)
		for i, value in enumerate(actual_values):
			if i != idx:
				self.assertEqual(value, 0)

	def test_chart_data_excludes_totals(self):
		# guards against "Total Budget"/"Total Actual" columns being swept into the
		# chart's period datasets, which would double-count against the real periods
		set_total_expense_zero(nowdate(), "cost_center")
		make_budget(
			budget_against="Cost Center", cost_center=COST_CENTER, budget_amount=120000, submit_budget=1
		)
		make_journal_entry(ACCOUNT, "_Test Bank - _TC", 50000, cost_center=COST_CENTER, submit=True)

		_columns, data, _, chart_data = self.run_report(period="Monthly", return_full=True)
		self.assertIsNotNone(chart_data)

		labels = chart_data["data"]["labels"]

		# exactly 12 monthly periods should be charted, not 12 + the 3 Total columns
		self.assertEqual(len(labels), 12)

		row = self.report_row(data, COST_CENTER)

		budget_values = next(
			d["values"] for d in chart_data["data"]["datasets"] if d["name"] == frappe._("Budget")
		)

		self.assertEqual(len(budget_values), 12)

		# sum of the charted monthly budgets should equal the row's total_budget,
		# not 2x it (which would happen if the Total column were also summed in)
		self.assertEqual(sum(budget_values), row["total_budget"])
