# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, nowdate

from erpnext.accounts.doctype.budget.test_budget import make_budget, set_total_expense_zero
from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.report.budget_variance_report.budget_variance_report import execute
from erpnext.accounts.utils import get_fiscal_year
from erpnext.tests.utils import ERPNextTestSuite


class TestBudgetVarianceReport(ERPNextTestSuite):
	def setUp(self):
		frappe.db.set_single_value("Accounts Settings", "use_legacy_budget_controller", False)
		self.company = "_Test Company"
		self.account = "_Test Account Cost for Goods Sold - _TC"
		self.cost_center = "_Test Cost Center - _TC"
		self.fiscal_year = get_fiscal_year(nowdate())[0]

	def _base_filters(self, **overrides):
		filters = frappe._dict(
			{
				"company": self.company,
				"from_fiscal_year": self.fiscal_year,
				"to_fiscal_year": self.fiscal_year,
				"period": "Monthly",
				"budget_against": "Cost Center",
				"budget_against_filter": [self.cost_center],
			}
		)
		filters.update(overrides)
		return filters

	def _find_row(self, data, dimension):
		"""Return the report row for a given budget_against dimension, or None."""
		matches = [row for row in data if row.get("budget_against") == dimension]
		return matches[0] if matches else None

	# ------------------------------------------------------------------
	# validate_filters
	# ------------------------------------------------------------------
	def test_invalid_budget_against_raises(self):
		"""An unknown accounting dimension must raise a ValidationError."""
		filters = self._base_filters(budget_against="Not A Real Dimension")
		self.assertRaises(frappe.ValidationError, execute, filters)

	def test_valid_dimensions_do_not_raise(self):
		"""Cost Center and Project are always valid budget_against dimensions."""
		for dimension in ("Cost Center", "Project"):
			filters = self._base_filters(budget_against=dimension, budget_against_filter=None)
			# Should not raise from validate_filters; execution returns a tuple.
			result = execute(filters)
			self.assertIsInstance(result, tuple)

	# ------------------------------------------------------------------
	# Budget distribution across periods
	# ------------------------------------------------------------------
	def test_monthly_budget_distribution_sums_to_annual(self):
		"""With Monthly periodicity the budget is spread across periods and the
		per-period budget values sum back to the submitted annual amount."""
		annual_amount = 240000
		set_total_expense_zero(nowdate(), "cost_center")
		make_budget(
			budget_against="Cost Center",
			budget_amount=annual_amount,
			do_not_save=False,
			submit_budget=True,
		)

		columns, data, _message, chart = execute(self._base_filters())

		self.assertTrue(columns)
		row = self._find_row(data, self.cost_center)
		self.assertIsNotNone(row)
		self.assertEqual(row.get("account"), self.account)

		# Total budget for the year equals the annual amount regardless of split.
		self.assertAlmostEqual(flt(row.get("total_budget")), annual_amount, places=2)

		# A calendar fiscal year has 12 months -> 12 equal monthly slices.
		monthly = annual_amount / 12.0
		budget_period_fields = [
			f for f in row if f.startswith("budget_") and not f.startswith("budget_against")
		]
		self.assertEqual(len(budget_period_fields), 12)
		for field in budget_period_fields:
			self.assertAlmostEqual(flt(row.get(field)), monthly, places=2)

		# Period budget fields should sum to the annual amount as well.
		summed = sum(flt(row.get(f)) for f in budget_period_fields)
		self.assertAlmostEqual(summed, annual_amount, places=2)

		# Chart data mirrors the report when there is data.
		self.assertIsNotNone(chart)
		self.assertIn("data", chart)

	# ------------------------------------------------------------------
	# Periodicity: column counts change, budget total invariant
	# ------------------------------------------------------------------
	def test_periodicity_changes_period_count_but_not_total(self):
		annual_amount = 240000
		set_total_expense_zero(nowdate(), "cost_center")
		make_budget(
			budget_against="Cost Center",
			budget_amount=annual_amount,
			do_not_save=False,
			submit_budget=True,
		)

		# Monthly: 12 budget period columns + totals row.
		monthly_cols, monthly_data, _m1, _c1 = execute(self._base_filters(period="Monthly"))
		monthly_budget_cols = [
			c
			for c in monthly_cols
			if c.get("fieldname", "").startswith("budget_")
			and not c.get("fieldname", "").startswith("budget_against")
		]
		self.assertEqual(len(monthly_budget_cols), 12)

		# Quarterly: a calendar year yields 4 quarters.
		quarterly_cols, quarterly_data, _m2, _c2 = execute(self._base_filters(period="Quarterly"))
		quarterly_budget_cols = [
			c
			for c in quarterly_cols
			if c.get("fieldname", "").startswith("budget_")
			and not c.get("fieldname", "").startswith("budget_against")
		]
		self.assertEqual(len(quarterly_budget_cols), 4)

		# Yearly: a single period.
		yearly_cols, yearly_data, _m3, _c3 = execute(self._base_filters(period="Yearly"))
		yearly_budget_cols = [
			c
			for c in yearly_cols
			if c.get("fieldname", "").startswith("budget_")
			and not c.get("fieldname", "").startswith("budget_against")
		]
		self.assertEqual(len(yearly_budget_cols), 1)

		# Fewer, larger periods -> fewer columns.
		self.assertGreater(len(monthly_budget_cols), len(quarterly_budget_cols))
		self.assertGreater(len(quarterly_budget_cols), len(yearly_budget_cols))

		# The total budget is invariant across periodicities.
		monthly_row = self._find_row(monthly_data, self.cost_center)
		quarterly_row = self._find_row(quarterly_data, self.cost_center)
		yearly_row = self._find_row(yearly_data, self.cost_center)

		self.assertAlmostEqual(flt(monthly_row.get("total_budget")), annual_amount, places=2)
		self.assertAlmostEqual(flt(quarterly_row.get("total_budget")), annual_amount, places=2)

		# Yearly rows expose the budget through the single period field (no totals).
		yearly_budget = sum(
			flt(yearly_row.get(f))
			for f in yearly_row
			if f.startswith("budget_") and not f.startswith("budget_against")
		)
		self.assertAlmostEqual(yearly_budget, annual_amount, places=2)

	def test_quarterly_budget_sums_to_annual(self):
		annual_amount = 240000
		set_total_expense_zero(nowdate(), "cost_center")
		make_budget(
			budget_against="Cost Center",
			budget_amount=annual_amount,
			do_not_save=False,
			submit_budget=True,
		)

		_columns, data, _message, _chart = execute(self._base_filters(period="Quarterly"))
		row = self._find_row(data, self.cost_center)
		self.assertIsNotNone(row)

		quarter_fields = [f for f in row if f.startswith("budget_") and not f.startswith("budget_against")]
		summed = sum(flt(row.get(f)) for f in quarter_fields)
		self.assertAlmostEqual(summed, annual_amount, places=2)

	# ------------------------------------------------------------------
	# Actual vs budget variance
	# ------------------------------------------------------------------
	def test_actual_amount_and_variance(self):
		"""An expense booked to the budgeted account + cost center shows up as the
		actual, and variance = budget - actual over the year."""
		annual_amount = 240000
		actual_amount = 30000

		set_total_expense_zero(nowdate(), "cost_center")
		make_budget(
			budget_against="Cost Center",
			budget_amount=annual_amount,
			do_not_save=False,
			submit_budget=True,
		)

		make_journal_entry(
			self.account,
			"_Test Bank - _TC",
			actual_amount,
			self.cost_center,
			posting_date=nowdate(),
			submit=True,
		)

		_columns, data, _message, chart = execute(self._base_filters(period="Monthly"))
		row = self._find_row(data, self.cost_center)
		self.assertIsNotNone(row)

		# Aggregate actual across all periods equals the booked expense.
		self.assertAlmostEqual(flt(row.get("total_actual")), actual_amount, places=2)
		self.assertAlmostEqual(flt(row.get("total_budget")), annual_amount, places=2)
		self.assertAlmostEqual(flt(row.get("total_variance")), annual_amount - actual_amount, places=2)

		# The expense lands in exactly one period; that period's variance is
		# budget - actual and the rest carry zero actuals.
		actual_fields = [f for f in row if f.startswith("actual_")]
		nonzero = [f for f in actual_fields if flt(row.get(f)) != 0]
		self.assertEqual(len(nonzero), 1)
		self.assertAlmostEqual(flt(row.get(nonzero[0])), actual_amount, places=2)

		# Chart actual dataset total reflects the booked expense.
		actual_dataset = next(d for d in chart["data"]["datasets"] if "Actual" in d["name"])
		self.assertAlmostEqual(sum(flt(v) for v in actual_dataset["values"]), actual_amount, places=2)

	def test_zero_actuals_when_no_expense(self):
		"""Without any GL postings the actual columns and totals are zero."""
		annual_amount = 120000
		set_total_expense_zero(nowdate(), "cost_center")
		make_budget(
			budget_against="Cost Center",
			budget_amount=annual_amount,
			do_not_save=False,
			submit_budget=True,
		)

		_columns, data, _message, _chart = execute(self._base_filters(period="Monthly"))
		row = self._find_row(data, self.cost_center)
		self.assertIsNotNone(row)

		self.assertAlmostEqual(flt(row.get("total_actual")), 0, places=2)
		self.assertAlmostEqual(flt(row.get("total_variance")), annual_amount, places=2)
		for field in [f for f in row if f.startswith("actual_")]:
			self.assertAlmostEqual(flt(row.get(field)), 0, places=2)

	# ------------------------------------------------------------------
	# Cumulative display
	# ------------------------------------------------------------------
	def test_show_cumulative_is_non_decreasing(self):
		"""With show_cumulative the per-period budget runs as a non-decreasing
		total that ends at the annual amount."""
		annual_amount = 240000
		set_total_expense_zero(nowdate(), "cost_center")
		make_budget(
			budget_against="Cost Center",
			budget_amount=annual_amount,
			do_not_save=False,
			submit_budget=True,
		)

		columns, data, _message, _chart = execute(self._base_filters(period="Monthly", show_cumulative=1))
		row = self._find_row(data, self.cost_center)
		self.assertIsNotNone(row)

		# Read the report's actual per-period budget columns, in chronological order.
		period_fields = [
			c["fieldname"]
			for c in columns
			if c.get("fieldname", "").startswith("budget_")
			and not c.get("fieldname", "").startswith("budget_against")
		]
		self.assertEqual(len(period_fields), 12)
		cumulative = [flt(row.get(f)) for f in period_fields]

		# Each period's running budget is >= the previous (monotonically non-decreasing).
		for i in range(1, len(cumulative)):
			self.assertGreaterEqual(cumulative[i], cumulative[i - 1])

		# It genuinely accumulates: starts at one month's budget, ends at the annual
		# amount (a broken show_cumulative would leave the last column at ~one month).
		self.assertAlmostEqual(cumulative[0], annual_amount / 12.0, places=2)
		self.assertAlmostEqual(cumulative[-1], annual_amount, places=2)
		self.assertGreater(cumulative[-1], cumulative[0])

		# The grand total still equals the annual amount.
		self.assertAlmostEqual(flt(row.get("total_budget")), annual_amount, places=2)

	# ------------------------------------------------------------------
	# Cost center with children expansion
	# ------------------------------------------------------------------
	def test_cost_center_with_children_rolls_up_child_actuals(self):
		"""A budget on a parent (group) cost center should pick up actuals booked
		to a child cost center via get_cost_center_with_children."""
		parent_cc = "_Test Company - _TC"  # root group cost center
		child_cc = "_Test Cost Center 2 - _TC"
		annual_amount = 360000
		actual_amount = 25000

		make_budget(
			budget_against="Cost Center",
			cost_center=parent_cc,
			budget_amount=annual_amount,
			do_not_save=False,
			submit_budget=True,
		)

		filters = self._base_filters(
			period="Monthly",
			budget_against_filter=[parent_cc],
		)

		# Baseline actuals before booking the new child expense (the test DB may
		# carry unrelated fixture expenses; assert on the delta instead).
		_c0, data_before, _m0, _ch0 = execute(filters)
		row_before = self._find_row(data_before, parent_cc)
		self.assertIsNotNone(row_before)
		baseline_actual = flt(row_before.get("total_actual"))
		self.assertAlmostEqual(flt(row_before.get("total_budget")), annual_amount, places=2)

		# Book the actual against the *child* cost center.
		make_journal_entry(
			self.account,
			"_Test Bank - _TC",
			actual_amount,
			child_cc,
			posting_date=nowdate(),
			submit=True,
		)

		_columns, data, _message, _chart = execute(filters)
		row = self._find_row(data, parent_cc)
		self.assertIsNotNone(row)

		# Child cost-center expense rolls into the parent budget's actuals.
		self.assertAlmostEqual(flt(row.get("total_actual")) - baseline_actual, actual_amount, places=2)
		self.assertAlmostEqual(flt(row.get("total_budget")), annual_amount, places=2)
		self.assertAlmostEqual(
			flt(row.get("total_variance")),
			annual_amount - flt(row.get("total_actual")),
			places=2,
		)

	# ------------------------------------------------------------------
	# Empty result handling
	# ------------------------------------------------------------------
	def test_no_budget_returns_empty_data(self):
		"""When the filtered dimension has no submitted budget the report still
		returns columns but an empty data set and no chart."""
		set_total_expense_zero(nowdate(), "cost_center")
		# Use a cost center that has no budget on the test account.
		filters = self._base_filters(
			period="Monthly",
			budget_against_filter=["_Test Write Off Cost Center - _TC"],
		)
		columns, data, _message, chart = execute(filters)

		self.assertTrue(columns)
		self.assertEqual(data, [])
		self.assertIsNone(chart)
