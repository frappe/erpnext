# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
from frappe.utils import today

from erpnext.accounts.report.financial_ratios.financial_ratios import (
	calculate_ratio,
	execute,
	get_columns,
	setup_filters,
	update_balances,
)
from erpnext.accounts.report.financial_statements import get_period_list
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.tests.utils import ERPNextTestSuite


class TestCalculateRatio(ERPNextTestSuite):
	"""Pure-function tests for the division guard helper.

	calculate_ratio(value, denominator, precision):
	        - returns flt(value / denominator, precision) when denominator is truthy
	        - returns 0 when denominator evaluates to falsy (zero / None)
	"""

	def test_normal_division(self):
		self.assertAlmostEqual(calculate_ratio(10, 4, 2), 2.5, places=2)

	def test_division_rounds_to_precision(self):
		# 10 / 3 = 3.333..., precision 2 -> 3.33
		self.assertAlmostEqual(calculate_ratio(10, 3, 2), 3.33, places=2)
		# precision 0 -> rounds to nearest integer
		self.assertAlmostEqual(calculate_ratio(10, 3, 0), 3.0, places=2)

	def test_zero_denominator_returns_zero(self):
		# The guard `if flt(denominator)` is the critical branch: must not raise
		# ZeroDivisionError and must return 0 rather than None.
		self.assertEqual(calculate_ratio(100, 0, 2), 0)

	def test_zero_denominator_with_zero_value_returns_zero(self):
		self.assertEqual(calculate_ratio(0, 0, 2), 0)

	def test_none_denominator_returns_zero(self):
		# flt(None) -> 0.0 which is falsy, so the guard returns 0.
		self.assertEqual(calculate_ratio(100, None, 2), 0)

	def test_zero_numerator_nonzero_denominator(self):
		self.assertEqual(calculate_ratio(0, 5, 2), 0.0)

	def test_none_numerator_is_coerced_to_zero(self):
		# flt(None) -> 0.0 in the numerator path.
		self.assertEqual(calculate_ratio(None, 5, 2), 0.0)

	def test_negative_value(self):
		self.assertAlmostEqual(calculate_ratio(-10, 4, 2), -2.5, places=2)

	def test_negative_denominator(self):
		self.assertAlmostEqual(calculate_ratio(10, -4, 2), -2.5, places=2)

	def test_both_negative(self):
		self.assertAlmostEqual(calculate_ratio(-10, -4, 2), 2.5, places=2)

	def test_float_inputs(self):
		self.assertAlmostEqual(calculate_ratio(7.5, 2.5, 2), 3.0, places=2)


class TestUpdateBalances(ERPNextTestSuite):
	"""Pure-function tests for the root-type accumulation dispatch.

	update_balances mutates ratio_dict / total_dict / net_dict in place based on
	root_type ("Asset", "Liability", "Income", "Expense") and account_type. It
	operates purely on in-memory lists of dicts, so it can be exercised with
	synthetic GL-shaped rows without touching the database.
	"""

	YEAR = "fy_2023"

	def test_total_picked_from_root_group_row(self):
		# A row with no parent_account and is_group=True is treated as the root
		# total for that root_type.
		root_data = [
			{"parent_account": None, "is_group": True, self.YEAR: 5000},
		]
		ratio_dict, total_dict = {}, {}
		update_balances(ratio_dict, total_dict, "Current Asset", self.YEAR, root_data, "Asset", {}, 0)
		self.assertEqual(total_dict[self.YEAR], 5000)

	def test_direct_expense_total_is_sign_flipped(self):
		# For account_type "Direct Expense" the root total is negated.
		root_data = [
			{"parent_account": None, "is_group": True, self.YEAR: 1200},
		]
		ratio_dict, total_dict = {}, {}
		update_balances(ratio_dict, total_dict, "Direct Expense", self.YEAR, root_data, "Expense", {}, 0)
		self.assertEqual(total_dict[self.YEAR], -1200)

	def test_asset_group_account_type_match_sets_ratio(self):
		# Asset/Liability branch: a group account whose account_type matches the
		# requested account_type populates ratio_dict.
		root_data = [
			{"parent_account": None, "is_group": True, self.YEAR: 9000},
			{
				"parent_account": "Application of Funds",
				"account_type": "Current Asset",
				"is_group": True,
				self.YEAR: 3000,
			},
		]
		ratio_dict, total_dict = {}, {}
		update_balances(ratio_dict, total_dict, "Current Asset", self.YEAR, root_data, "Asset", {}, 0)
		self.assertEqual(ratio_dict[self.YEAR], 3000)
		self.assertEqual(total_dict[self.YEAR], 9000)

	def test_asset_quick_asset_accumulates_bank_cash_receivable(self):
		# Quick asset = sum of non-group Bank + Cash + Receivable leaf accounts.
		root_data = [
			{"parent_account": "Current Assets", "account_type": "Bank", "is_group": False, self.YEAR: 1000},
			{"parent_account": "Current Assets", "account_type": "Cash", "is_group": False, self.YEAR: 500},
			{
				"parent_account": "Current Assets",
				"account_type": "Receivable",
				"is_group": False,
				self.YEAR: 250,
			},
			# Stock is NOT a quick asset and must be excluded.
			{"parent_account": "Current Assets", "account_type": "Stock", "is_group": False, self.YEAR: 9999},
		]
		ratio_dict, total_dict, net_dict = {}, {}, {}
		update_balances(ratio_dict, total_dict, "Current Asset", self.YEAR, root_data, "Asset", net_dict, 0)
		self.assertEqual(net_dict[self.YEAR], 1750)

	def test_asset_group_bank_account_excluded_from_quick_asset(self):
		# The Bank/Cash/Receivable accumulation only counts leaf (non-group) rows.
		root_data = [
			{"parent_account": "Current Assets", "account_type": "Bank", "is_group": True, self.YEAR: 1000},
		]
		ratio_dict, total_dict, net_dict = {}, {}, {}
		update_balances(ratio_dict, total_dict, "Current Asset", self.YEAR, root_data, "Asset", net_dict, 0)
		self.assertNotIn(self.YEAR, net_dict)

	def test_income_group_match_accumulates_into_ratio(self):
		# Income branch: group rows matching account_type accumulate into ratio_dict.
		root_data = [
			{"parent_account": None, "is_group": True, self.YEAR: 8000},
			{"parent_account": "Income", "account_type": "Direct Income", "is_group": True, self.YEAR: 6000},
		]
		ratio_dict, total_dict = {}, {}
		update_balances(ratio_dict, total_dict, "Direct Income", self.YEAR, root_data, "Income", {}, 0)
		self.assertEqual(ratio_dict[self.YEAR], 6000)
		self.assertEqual(total_dict[self.YEAR], 8000)

	def test_expense_cogs_matches_group_and_leaf(self):
		# Expense + "Cost of Goods Sold" branch matches on account_type
		# regardless of is_group, accumulating into ratio_dict.
		root_data = [
			{"parent_account": None, "is_group": True, self.YEAR: 7000},
			{
				"parent_account": "Expenses",
				"account_type": "Cost of Goods Sold",
				"is_group": True,
				self.YEAR: 2000,
			},
			{
				"parent_account": "Cost of Goods Sold",
				"account_type": "Cost of Goods Sold",
				"is_group": False,
				self.YEAR: 1000,
			},
		]
		ratio_dict, total_dict = {}, {}
		update_balances(ratio_dict, total_dict, "Cost of Goods Sold", self.YEAR, root_data, "Expense", {}, 0)
		self.assertEqual(ratio_dict[self.YEAR], 3000)
		self.assertEqual(total_dict[self.YEAR], 7000)

	def test_expense_direct_expense_else_branch(self):
		# Expense + a non-COGS account_type hits the final else branch, which
		# only sets ratio_dict from matching group rows.
		root_data = [
			{
				"parent_account": "Expenses",
				"account_type": "Direct Expense",
				"is_group": True,
				self.YEAR: 1500,
			},
		]
		ratio_dict, total_dict = {}, {}
		update_balances(ratio_dict, total_dict, "Direct Expense", self.YEAR, root_data, "Expense", {}, 0)
		self.assertEqual(ratio_dict[self.YEAR], 1500)

	def test_non_matching_account_type_leaves_ratio_empty(self):
		# A group row whose account_type does not match should not populate
		# ratio_dict.
		root_data = [
			{
				"parent_account": "Application of Funds",
				"account_type": "Fixed Asset",
				"is_group": True,
				self.YEAR: 4000,
			},
		]
		ratio_dict, total_dict = {}, {}
		update_balances(ratio_dict, total_dict, "Current Asset", self.YEAR, root_data, "Asset", {}, 0)
		self.assertNotIn(self.YEAR, ratio_dict)

	def test_empty_root_data_is_a_noop(self):
		ratio_dict, total_dict, net_dict = {}, {}, {}
		update_balances(ratio_dict, total_dict, "Current Asset", self.YEAR, [], "Asset", net_dict, 0)
		self.assertEqual(ratio_dict, {})
		self.assertEqual(total_dict, {})
		self.assertEqual(net_dict, {})


class TestFinancialRatiosColumns(ERPNextTestSuite):
	"""get_columns builds the report columns + year-key list from a period list."""

	def test_columns_structure_and_year_keys(self):
		# Synthetic period list shaped like get_period_list output.
		period_list = [
			frappe._dict(key="fy_2022", label="FY 2022"),
			frappe._dict(key="fy_2023", label="FY 2023"),
		]
		columns, years = get_columns(period_list)

		# First column is always the "Ratios" label column.
		self.assertEqual(columns[0]["fieldname"], "ratio")
		self.assertEqual(columns[0]["fieldtype"], "Data")

		# One Float column per period, in order.
		self.assertEqual(len(columns), 3)
		self.assertEqual(columns[1]["fieldname"], "fy_2022")
		self.assertEqual(columns[1]["label"], "FY 2022")
		self.assertEqual(columns[1]["fieldtype"], "Float")
		self.assertEqual(columns[2]["fieldname"], "fy_2023")

		# years mirrors the period keys, in order.
		self.assertEqual(years, ["fy_2022", "fy_2023"])

	def test_empty_period_list_yields_only_label_column(self):
		columns, years = get_columns([])
		self.assertEqual(len(columns), 1)
		self.assertEqual(columns[0]["fieldname"], "ratio")
		self.assertEqual(years, [])


class TestSetupFilters(ERPNextTestSuite, AccountsTestMixin):
	"""setup_filters back-fills period_start_date / period_end_date from the
	fiscal year when they are not supplied."""

	def setUp(self):
		self.create_company()

	def get_active_fiscal_year(self):
		active_fy = frappe.db.get_all(
			"Fiscal Year",
			filters={
				"disabled": 0,
				"year_start_date": ("<=", today()),
				"year_end_date": (">=", today()),
			},
		)[0]
		return frappe.get_doc("Fiscal Year", active_fy.name)

	def test_backfills_dates_from_fiscal_year(self):
		fy = self.get_active_fiscal_year()
		filters = frappe._dict(from_fiscal_year=fy.name, to_fiscal_year=fy.name)

		setup_filters(filters)

		self.assertEqual(filters["period_start_date"], fy.year_start_date)
		self.assertEqual(filters["period_end_date"], fy.year_end_date)

	def test_preserves_supplied_dates(self):
		fy = self.get_active_fiscal_year()
		filters = frappe._dict(
			from_fiscal_year=fy.name,
			to_fiscal_year=fy.name,
			period_start_date="2023-04-01",
			period_end_date="2024-03-31",
		)

		setup_filters(filters)

		# Pre-supplied dates must be left untouched.
		self.assertEqual(filters["period_start_date"], "2023-04-01")
		self.assertEqual(filters["period_end_date"], "2024-03-31")


class TestFinancialRatiosIntegration(ERPNextTestSuite, AccountsTestMixin):
	"""Light end-to-end smoke test of execute(filters).

	Mirrors the proven Profit and Loss Statement test wiring: a company from
	AccountsTestMixin + the active fiscal year. With no GL activity the report
	must still return a (columns, data) tuple, with non-empty columns and the
	expected ratio-section headers, without raising (in particular without a
	ZeroDivisionError from any ratio whose denominator is zero).
	"""

	def setUp(self):
		self.create_company()

	def get_active_fiscal_year(self):
		active_fy = frappe.db.get_all(
			"Fiscal Year",
			filters={
				"disabled": 0,
				"year_start_date": ("<=", today()),
				"year_end_date": (">=", today()),
			},
		)[0]
		return frappe.get_doc("Fiscal Year", active_fy.name)

	def get_report_filters(self):
		fy = self.get_active_fiscal_year()
		return frappe._dict(
			company=self.company,
			from_fiscal_year=fy.name,
			to_fiscal_year=fy.name,
			period_start_date=fy.year_start_date,
			period_end_date=fy.year_end_date,
			filter_based_on="Fiscal Year",
			periodicity="Yearly",
		)

	def test_execute_returns_columns_and_data(self):
		filters = self.get_report_filters()

		result = execute(filters)

		# execute returns a (columns, data) tuple.
		self.assertEqual(len(result), 2)
		columns, data = result

		# Columns are non-empty and the first is the "Ratios" label column.
		self.assertTrue(columns)
		self.assertEqual(columns[0]["fieldname"], "ratio")

		# Period columns exist for the requested fiscal year.
		period_list = get_period_list(
			filters.from_fiscal_year,
			filters.to_fiscal_year,
			filters.period_start_date,
			filters.period_end_date,
			filters.filter_based_on,
			filters.periodicity,
			company=filters.company,
		)
		self.assertEqual(len(columns), 1 + len(period_list))

		# Data contains the three ratio-section header rows. Sort before
		# comparing so the assertion is order-independent across databases.
		section_labels = sorted(
			row["ratio"] for row in data if isinstance(row, dict) and len(row) == 1 and "ratio" in row
		)
		self.assertEqual(
			section_labels,
			sorted(["Liquidity Ratios", "Solvency Ratios", "Turnover Ratios"]),
		)
