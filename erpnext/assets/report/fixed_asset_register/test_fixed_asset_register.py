# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_months, getdate, nowdate

from erpnext.assets.doctype.asset.test_asset import create_asset
from erpnext.assets.report.fixed_asset_register.fixed_asset_register import (
	execute,
	get_columns,
	get_conditions,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestFixedAssetRegister(ERPNextTestSuite):
	"""Tests for the Fixed Asset Register script report.

	The report's value columns (`depreciated_amount`, `asset_value` adjustments)
	depend on GL Entries produced by depreciation/revaluation. The assets created
	here intentionally have `calculate_depreciation=0` and no GL Entries, so the
	depreciation and revaluation maps are empty and `asset_value` collapses to
	`net_purchase_amount - opening_accumulated_depreciation`. This keeps the
	numeric assertions deterministic without heavy GL fixtures.
	"""

	# ------------------------------------------------------------------ #
	# get_conditions (pure dict builder)
	# ------------------------------------------------------------------ #

	def test_conditions_defaults(self):
		"""With no status/period filters, only docstatus + company are constrained."""
		conditions = get_conditions(frappe._dict({"company": "_Test Company"}))

		self.assertEqual(conditions["docstatus"], 1)
		self.assertEqual(conditions["company"], "_Test Company")
		# No status filter supplied -> no status condition.
		self.assertNotIn("status", conditions)
		# No period filter supplied -> no date condition on purchase_date.
		self.assertNotIn("purchase_date", conditions)
		self.assertNotIn("available_for_use_date", conditions)

	def test_conditions_status_in_location(self):
		"""status='In Location' must exclude disposed assets via a 'not in' operand."""
		conditions = get_conditions(frappe._dict({"company": "_Test Company", "status": "In Location"}))

		self.assertIn("status", conditions)
		operand, statuses = conditions["status"]
		self.assertEqual(operand, "not in")
		self.assertEqual(sorted(statuses), ["Capitalized", "Scrapped", "Sold"])

	def test_conditions_status_disposed(self):
		"""status='Disposed' must include only disposed assets via an 'in' operand."""
		conditions = get_conditions(frappe._dict({"company": "_Test Company", "status": "Disposed"}))

		self.assertIn("status", conditions)
		operand, statuses = conditions["status"]
		self.assertEqual(operand, "in")
		self.assertEqual(sorted(statuses), ["Capitalized", "Scrapped", "Sold"])

	def test_conditions_date_range_explicit(self):
		"""Date Range with explicit bounds uses the scrubbed date_based_on field."""
		conditions = get_conditions(
			frappe._dict(
				{
					"company": "_Test Company",
					"filter_based_on": "Date Range",
					"date_based_on": "Purchase Date",
					"from_date": "2021-01-01",
					"to_date": "2021-12-31",
				}
			)
		)

		self.assertIn("purchase_date", conditions)
		operand, bounds = conditions["purchase_date"]
		self.assertEqual(operand, "between")
		self.assertEqual(bounds, ["2021-01-01", "2021-12-31"])

	def test_conditions_date_range_defaults_to_trailing_year(self):
		"""Date Range without bounds defaults to the trailing 12 months ending today."""
		filters = frappe._dict({"company": "_Test Company", "filter_based_on": "Date Range"})
		conditions = get_conditions(filters)

		self.assertIn("purchase_date", conditions)
		operand, bounds = conditions["purchase_date"]
		self.assertEqual(operand, "between")
		# get_conditions mutates the filters dict with the computed defaults.
		self.assertEqual(filters.from_date, add_months(nowdate(), -12))
		self.assertEqual(filters.to_date, nowdate())
		self.assertEqual(bounds, [filters.from_date, filters.to_date])

	def test_conditions_date_based_on_available_for_use_date(self):
		"""date_based_on='Available For Use Date' switches the constrained field."""
		conditions = get_conditions(
			frappe._dict(
				{
					"company": "_Test Company",
					"filter_based_on": "Date Range",
					"date_based_on": "Available For Use Date",
					"from_date": "2021-01-01",
					"to_date": "2021-12-31",
				}
			)
		)

		self.assertIn("available_for_use_date", conditions)
		self.assertNotIn("purchase_date", conditions)

	def test_conditions_fiscal_year(self):
		"""Fiscal Year filter resolves to a between-condition on the year window."""
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"filter_based_on": "Fiscal Year",
				"date_based_on": "Purchase Date",
				"from_fiscal_year": "_Test Fiscal Year 2021",
				"to_fiscal_year": "_Test Fiscal Year 2021",
			}
		)
		conditions = get_conditions(filters)

		self.assertIn("purchase_date", conditions)
		operand, bounds = conditions["purchase_date"]
		self.assertEqual(operand, "between")
		self.assertEqual(bounds[0], getdate("2021-01-01"))
		self.assertEqual(bounds[1], getdate("2021-12-31"))

	def test_conditions_extra_filters(self):
		"""only_existing_assets / asset_category / cost_center propagate to conditions."""
		conditions = get_conditions(
			frappe._dict(
				{
					"company": "_Test Company",
					"only_existing_assets": 1,
					"asset_category": "Computers",
					"cost_center": "_Test Cost Center - _TC",
				}
			)
		)

		self.assertEqual(conditions["asset_type"], "Existing Asset")
		self.assertEqual(conditions["asset_category"], "Computers")
		self.assertEqual(conditions["cost_center"], "_Test Cost Center - _TC")

	# ------------------------------------------------------------------ #
	# get_columns
	# ------------------------------------------------------------------ #

	def test_columns_asset_level(self):
		"""Asset-level columns expose the Asset ID link column."""
		columns = get_columns(frappe._dict({"group_by": "--Select a group--"}))
		fieldnames = [c["fieldname"] for c in columns]

		self.assertIn("asset_id", fieldnames)
		self.assertIn("asset_value", fieldnames)
		self.assertIn("net_purchase_amount", fieldnames)

	def test_columns_group_by(self):
		"""Group-by columns lead with the scrubbed group field and drop per-asset cols."""
		columns = get_columns(frappe._dict({"group_by": "Asset Category"}))
		fieldnames = [c["fieldname"] for c in columns]

		self.assertEqual(columns[0]["fieldname"], "asset_category")
		self.assertNotIn("asset_id", fieldnames)
		self.assertIn("asset_value", fieldnames)

	# ------------------------------------------------------------------ #
	# execute (asset-level)
	# ------------------------------------------------------------------ #

	def _base_filters(self, **overrides):
		filters = {
			"company": "_Test Company",
			"status": "In Location",
			"group_by": "--Select a group--",
			"include_default_book_assets": 0,
		}
		filters.update(overrides)
		return frappe._dict(filters)

	def test_execute_returns_four_tuple(self):
		"""execute() returns (columns, data, message, chart)."""
		result = execute(self._base_filters())

		self.assertEqual(len(result), 4)
		columns, data, message, chart = result
		self.assertTrue(columns)
		self.assertIsInstance(data, list)
		self.assertIsNone(message)

	def test_execute_includes_created_asset(self):
		"""A submitted existing asset shows up with its gross value as asset_value."""
		asset = create_asset(
			asset_name="FAR Asset A",
			net_purchase_amount=120000,
			purchase_amount=120000,
			location="Test Location",
			asset_category="Computers",
			submit=1,
		)

		_columns, data, _message, _chart = execute(self._base_filters())

		row = next((d for d in data if d["asset_id"] == asset.name), None)
		self.assertIsNotNone(row, "Created asset missing from report data")
		self.assertAlmostEqual(row["net_purchase_amount"], 120000, places=2)
		# No depreciation / revaluation GL entries -> asset_value == net purchase amount.
		self.assertAlmostEqual(row["asset_value"], 120000, places=2)
		self.assertEqual(row["asset_category"], "Computers")
		self.assertEqual(row["location"], "Test Location")

	def test_execute_disposed_filter_excludes_active_asset(self):
		"""status='Disposed' must exclude a plain submitted (non-disposed) asset."""
		asset = create_asset(
			asset_name="FAR Asset B",
			net_purchase_amount=50000,
			purchase_amount=50000,
			submit=1,
		)

		_columns, data, _message, _chart = execute(self._base_filters(status="Disposed"))

		ids = [d["asset_id"] for d in data]
		self.assertNotIn(asset.name, ids)

	def test_execute_date_range_excluding_all_assets(self):
		"""A date window before any asset's purchase date yields empty data, no crash."""
		create_asset(
			asset_name="FAR Asset C",
			net_purchase_amount=70000,
			purchase_amount=70000,
			purchase_date="2020-05-05",
			submit=1,
		)

		filters = self._base_filters(
			filter_based_on="Date Range",
			date_based_on="Purchase Date",
			from_date="1999-01-01",
			to_date="1999-12-31",
		)
		_columns, data, _message, _chart = execute(filters)

		self.assertEqual(data, [])

	# ------------------------------------------------------------------ #
	# execute (group-by aggregation)
	# ------------------------------------------------------------------ #

	def test_execute_group_by_asset_category_aggregates(self):
		"""Group-by Asset Category sums net_purchase_amount across that category's assets."""
		create_asset(
			asset_name="FAR Cat Asset 1",
			net_purchase_amount=10000,
			purchase_amount=10000,
			asset_category="Computers",
			submit=1,
		)
		create_asset(
			asset_name="FAR Cat Asset 2",
			net_purchase_amount=25000,
			purchase_amount=25000,
			asset_category="Computers",
			submit=1,
		)

		filters = self._base_filters(group_by="Asset Category", asset_category="Computers")
		_columns, data, _message, chart = execute(filters)

		# Aggregated reports return no chart.
		self.assertEqual(chart, {})

		computers = [d for d in data if d.get("asset_category") == "Computers"]
		self.assertEqual(len(computers), 1, "Category rows should be collapsed to one per category")
		row = computers[0]
		# Filtered to the Computers category, so the row total equals the sum of
		# every Computers asset's net purchase amount (>= the two we just created).
		expected_total = sum(
			frappe.get_all(
				"Asset",
				filters={
					"docstatus": 1,
					"company": "_Test Company",
					"asset_category": "Computers",
					# Mirror the report's status="In Location" (exclude disposed) condition.
					"status": ["not in", ["Sold", "Scrapped", "Capitalized"]],
				},
				pluck="net_purchase_amount",
			)
		)
		self.assertAlmostEqual(row["net_purchase_amount"], expected_total, places=2)
		self.assertGreaterEqual(row["net_purchase_amount"], 35000)

	def test_execute_group_by_location(self):
		"""Group-by Location returns per-location rows for the created assets."""
		create_asset(
			asset_name="FAR Loc Asset 1",
			net_purchase_amount=15000,
			purchase_amount=15000,
			location="Test Location",
			submit=1,
		)
		create_asset(
			asset_name="FAR Loc Asset 2",
			net_purchase_amount=18000,
			purchase_amount=18000,
			location="Test Location 2",
			submit=1,
		)

		filters = self._base_filters(group_by="Location")
		_columns, data, _message, _chart = execute(filters)

		locations = sorted(d.get("location") for d in data if d.get("location"))
		self.assertIn("Test Location", locations)
		self.assertIn("Test Location 2", locations)
		# One aggregated row per location.
		self.assertEqual(len(locations), len(set(locations)))
