# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_months, getdate, nowdate

from erpnext.assets.doctype.asset.depreciation import get_asset_depr_schedule_name
from erpnext.assets.doctype.asset.test_asset import create_asset
from erpnext.assets.doctype.asset_depreciation_schedule.asset_depreciation_schedule import (
	get_asset_depr_schedule_doc,
)
from erpnext.assets.page.pending_depreciation.pending_depreciation import (
	create_depreciation_entries,
	get_pending_depreciation_assets,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestPendingDepreciation(ERPNextTestSuite):
	def setUp(self):
		# Asset with 3 monthly depreciations starting 2023-01-31
		self.asset = create_asset(
			asset_name="Test Pending Depr Asset",
			asset_category="Computers",
			calculate_depreciation=1,
			available_for_use_date="2023-01-01",
			depreciation_start_date="2023-01-31",
			frequency_of_depreciation=1,
			total_number_of_depreciations=3,
			net_purchase_amount=90000,
			submit=1,
		)
		self.depr_schedule = get_asset_depr_schedule_doc(self.asset.name, "Active")

	def tearDown(self):
		frappe.db.rollback()

	# ─── get_pending_depreciation_assets ────────────────────────────────────────

	def test_returns_asset_with_pending_entry(self):
		"""Asset appears when queried up to its first depreciation date."""
		rows = get_pending_depreciation_assets(date="2023-01-31", company="_Test Company")
		names = [r.asset for r in rows]
		self.assertIn(self.asset.name, names)

	def test_returns_multiple_pending_entries_summed(self):
		"""Querying a later date sums all pending depreciation amounts for the asset."""
		rows = get_pending_depreciation_assets(date="2023-03-31", company="_Test Company")
		row = next((r for r in rows if r.asset == self.asset.name), None)
		self.assertIsNotNone(row)
		# 3 pending entries × 30,000 each = 90,000
		self.assertAlmostEqual(row.pending_depreciation_amount, 90000, places=0)
		self.assertEqual(row.sch_end_idx, 3)

	def test_excludes_asset_before_first_depreciation_date(self):
		"""Asset is not returned if the queried date is before its first schedule."""
		rows = get_pending_depreciation_assets(date="2022-12-31", company="_Test Company")
		names = [r.asset for r in rows]
		self.assertNotIn(self.asset.name, names)

	def test_filter_by_asset_category(self):
		"""Only assets matching the requested asset_category are returned."""
		rows_matching = get_pending_depreciation_assets(
			date="2023-01-31",
			company="_Test Company",
			asset_category="Computers",
		)
		rows_other = get_pending_depreciation_assets(
			date="2023-01-31",
			company="_Test Company",
			asset_category="Furniture and Fixture",
		)
		self.assertTrue(any(r.asset == self.asset.name for r in rows_matching))
		self.assertFalse(any(r.asset == self.asset.name for r in rows_other))

	def test_filter_by_company(self):
		"""Assets of a different company are excluded."""
		rows = get_pending_depreciation_assets(
			date="2023-01-31",
			company="_Test Company 1",
		)
		names = [r.asset for r in rows]
		self.assertNotIn(self.asset.name, names)

	def test_row_contains_expected_fields(self):
		"""Each row must expose the fields required for the UI table."""
		rows = get_pending_depreciation_assets(date="2023-01-31", company="_Test Company")
		row = next((r for r in rows if r.asset == self.asset.name), None)
		self.assertIsNotNone(row)
		for field in (
			"depr_schedule_name",
			"asset",
			"asset_name",
			"asset_category",
			"depreciation_method",
			"next_depreciation_date",
			"pending_depreciation_amount",
			"sch_start_idx",
			"sch_end_idx",
		):
			self.assertIn(field, row, msg=f"Missing field: {field}")

	def test_excludes_already_posted_entries(self):
		"""After creating a depreciation entry, the asset no longer appears for that period."""
		create_depreciation_entries(
			depr_schedule_names=[self.depr_schedule.name],
			date="2023-01-31",
		)
		rows = get_pending_depreciation_assets(date="2023-01-31", company="_Test Company")
		names = [r.asset for r in rows]
		# Asset still pending for Feb and Mar; for Jan-only query it should not appear
		self.assertNotIn(self.asset.name, names)

	# ─── create_depreciation_entries ────────────────────────────────────────────

	def test_creates_journal_entry_for_selected_schedule(self):
		"""Calling create_depreciation_entries posts a Journal Entry for the schedule."""
		result = create_depreciation_entries(
			depr_schedule_names=[self.depr_schedule.name],
			date="2023-01-31",
		)
		self.assertEqual(len(result["success"]), 1)
		self.assertEqual(len(result["failed"]), 0)

		# Verify journal_entry is set on the first schedule row
		self.depr_schedule.reload()
		first_row = self.depr_schedule.depreciation_schedule[0]
		self.assertTrue(first_row.journal_entry, "Journal entry was not created")

	def test_returns_success_and_failed_lists(self):
		"""Return dict has 'success' and 'failed' keys."""
		result = create_depreciation_entries(
			depr_schedule_names=[self.depr_schedule.name],
			date="2023-03-31",
		)
		self.assertIn("success", result)
		self.assertIn("failed", result)

	def test_handles_json_string_input(self):
		"""depr_schedule_names can be passed as a JSON string (as Frappe serialises it)."""
		import json

		result = create_depreciation_entries(
			depr_schedule_names=json.dumps([self.depr_schedule.name]),
			date="2023-01-31",
		)
		self.assertEqual(len(result["success"]), 1)

	def test_invalid_schedule_name_goes_to_failed(self):
		"""A schedule name that has no pending entries ends up in failed list."""
		result = create_depreciation_entries(
			depr_schedule_names=["NONEXISTENT-SCHEDULE"],
			date="2023-01-31",
		)
		self.assertEqual(len(result["failed"]), 1)
		self.assertEqual(result["failed"][0]["name"], "NONEXISTENT-SCHEDULE")

	def test_bulk_creation_for_multiple_assets(self):
		"""Multiple schedules can be processed in one call."""
		asset2 = create_asset(
			asset_name="Test Pending Depr Asset 2",
			asset_category="Computers",
			calculate_depreciation=1,
			available_for_use_date="2023-01-01",
			depreciation_start_date="2023-01-31",
			frequency_of_depreciation=1,
			total_number_of_depreciations=3,
			net_purchase_amount=60000,
			submit=1,
		)
		schedule2 = get_asset_depr_schedule_doc(asset2.name, "Active")

		result = create_depreciation_entries(
			depr_schedule_names=[self.depr_schedule.name, schedule2.name],
			date="2023-01-31",
		)
		self.assertEqual(len(result["success"]), 2)
		self.assertEqual(len(result["failed"]), 0)

	def test_throws_when_no_schedules_provided(self):
		"""Passing an empty list raises a validation error."""
		self.assertRaises(
			frappe.ValidationError,
			create_depreciation_entries,
			depr_schedule_names=[],
			date="2023-01-31",
		)
