# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import cstr

from erpnext.assets.doctype.asset.test_asset import create_asset


class TestAssetShiftAllocation(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		create_asset_shift_factors()

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()

	def test_asset_shift_allocation(self):
		asset = create_asset(
			calculate_depreciation=1,
			available_for_use_date="2023-01-01",
			purchase_date="2023-01-01",
			gross_purchase_amount=120000,
			depreciation_start_date="2023-01-31",
			total_number_of_depreciations=12,
			frequency_of_depreciation=1,
			shift_based=1,
			submit=1,
		)

		expected_schedules = [
			["2023-01-31", 10000.0, 10000.0, "Single"],
			["2023-02-28", 10000.0, 20000.0, "Single"],
			["2023-03-31", 10000.0, 30000.0, "Single"],
			["2023-04-30", 10000.0, 40000.0, "Single"],
			["2023-05-31", 10000.0, 50000.0, "Single"],
			["2023-06-30", 10000.0, 60000.0, "Single"],
			["2023-07-31", 10000.0, 70000.0, "Single"],
			["2023-08-31", 10000.0, 80000.0, "Single"],
			["2023-09-30", 10000.0, 90000.0, "Single"],
			["2023-10-31", 10000.0, 100000.0, "Single"],
			["2023-11-30", 10000.0, 110000.0, "Single"],
			["2023-12-31", 10000.0, 120000.0, "Single"],
		]

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount, d.shift]
			for d in asset.get("schedules")
		]

		self.assertEqual(schedules, expected_schedules)

		asset_shift_allocation = frappe.get_doc(
			{"doctype": "Asset Shift Allocation", "asset": asset.name}
		).insert()

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount, d.shift]
			for d in asset_shift_allocation.get("depreciation_schedule")
		]

		self.assertEqual(schedules, expected_schedules)

		asset_shift_allocation = frappe.get_doc("Asset Shift Allocation", asset_shift_allocation.name)
		asset_shift_allocation.depreciation_schedule[4].shift = "Triple"
		asset_shift_allocation.save()

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount, d.shift]
			for d in asset_shift_allocation.get("depreciation_schedule")
		]

		expected_schedules = [
			["2023-01-31", 10000.0, 10000.0, "Single"],
			["2023-02-28", 10000.0, 20000.0, "Single"],
			["2023-03-31", 10000.0, 30000.0, "Single"],
			["2023-04-30", 10000.0, 40000.0, "Single"],
			["2023-05-31", 20000.0, 60000.0, "Triple"],
			["2023-06-30", 10000.0, 70000.0, "Single"],
			["2023-07-31", 10000.0, 80000.0, "Single"],
			["2023-08-31", 10000.0, 90000.0, "Single"],
			["2023-09-30", 10000.0, 100000.0, "Single"],
			["2023-10-31", 10000.0, 110000.0, "Single"],
			["2023-11-30", 10000.0, 120000.0, "Single"],
		]

		self.assertEqual(schedules, expected_schedules)

		asset_shift_allocation.submit()

		asset.reload()

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount, d.shift]
			for d in asset.get("schedules")
		]

		self.assertEqual(schedules, expected_schedules)


def create_asset_shift_factors():
	shifts = [
		{"doctype": "Asset Shift Factor", "shift_name": "Half", "shift_factor": 0.5, "default": 0},
		{"doctype": "Asset Shift Factor", "shift_name": "Single", "shift_factor": 1, "default": 1},
		{"doctype": "Asset Shift Factor", "shift_name": "Double", "shift_factor": 1.5, "default": 0},
		{"doctype": "Asset Shift Factor", "shift_name": "Triple", "shift_factor": 2, "default": 0},
	]

	for s in shifts:
		frappe.get_doc(s).insert()
