# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import cstr

from erpnext.assets.doctype.asset.depreciation import post_depreciation_entries
from erpnext.assets.doctype.asset.test_asset import create_asset
from erpnext.assets.doctype.asset_depreciation_schedule.asset_depreciation_schedule import (
	get_depr_schedule,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestAssetShiftAllocation(ERPNextTestSuite):
	def setUp(self):
		create_asset_shift_factors()

	def test_asset_shift_allocation(self):
		asset = create_asset(
			calculate_depreciation=1,
			available_for_use_date="2023-01-01",
			purchase_date="2023-01-01",
			net_purchase_amount=120000,
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
			for d in get_depr_schedule(asset.name, "Active")
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

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount, d.shift]
			for d in get_depr_schedule(asset.name, "Active")
		]

		self.assertEqual(schedules, expected_schedules)

	def test_cancel_restores_previous_schedule(self):
		asset = create_shift_based_asset()
		original_schedule = get_active_schedule(asset.name)
		allocation = make_shift_allocation(asset.name, {0: "Triple"})
		allocation.submit()
		self.assertEqual(get_active_schedule(asset.name)[0], ("2023-01-31", 20000.0, "Triple", None))

		allocation.cancel()
		self.assertEqual(get_active_schedule(asset.name), original_schedule)

		allocation = make_shift_allocation(asset.name, {0: "Triple"})
		allocation.submit()
		post_depreciation_entries(date="2023-01-31")
		self.assertRaisesRegex(frappe.ValidationError, "depreciation has been posted", allocation.cancel)

	def test_submit_uses_entries_posted_after_save(self):
		asset = create_shift_based_asset()
		allocation = make_shift_allocation(asset.name, {0: "Triple"})
		post_depreciation_entries(date="2023-01-31")
		self.assertRaisesRegex(frappe.ValidationError, "Shift cannot be changed", allocation.submit)

		allocation = make_shift_allocation(asset.name, {2: "Triple"})
		post_depreciation_entries(date="2023-02-28")
		allocation.submit()

		schedule = get_active_schedule(asset.name)
		self.assertTrue(schedule[0][3] and schedule[1][3])
		self.assertEqual(
			[row[1:3] for row in schedule[:3]], [(10000.0, "Single")] * 2 + [(20000.0, "Triple")]
		)
		self.assertEqual(len(schedule), 11)

	def test_increase_is_balanced_only_by_later_rows(self):
		asset = create_shift_based_asset()
		self.assertRaisesRegex(
			frappe.ValidationError, "cannot be balanced", make_shift_allocation, asset.name, {11: "Triple"}
		)

		allocation = make_shift_allocation(asset.name, {0: "Double"})
		amounts = [row.depreciation_amount for row in allocation.depreciation_schedule]
		self.assertEqual(amounts, [15000.0] + [10000.0] * 10 + [5000.0])

		frappe.db.delete("Asset Shift Factor", {"name": "Half"})
		self.assertRaisesRegex(
			frappe.ValidationError, "cannot be balanced", make_shift_allocation, asset.name, {0: "Double"}
		)


def create_shift_based_asset():
	return create_asset(
		calculate_depreciation=1,
		available_for_use_date="2023-01-01",
		purchase_date="2023-01-01",
		net_purchase_amount=120000,
		depreciation_start_date="2023-01-31",
		total_number_of_depreciations=12,
		frequency_of_depreciation=1,
		shift_based=1,
		submit=1,
	)


def make_shift_allocation(asset: str, shifts: dict[int, str]):
	allocation = frappe.get_doc({"doctype": "Asset Shift Allocation", "asset": asset}).insert()
	allocation = frappe.get_doc(allocation.doctype, allocation.name)
	for index, shift in shifts.items():
		allocation.depreciation_schedule[index].shift = shift
	allocation.save()
	return allocation


def get_active_schedule(asset: str) -> list[tuple]:
	return [
		(cstr(d.schedule_date), d.depreciation_amount, d.shift, d.journal_entry)
		for d in get_depr_schedule(asset, "Active")
	]


def create_asset_shift_factors():
	shifts = [
		{"doctype": "Asset Shift Factor", "shift_name": "Half", "shift_factor": 0.5, "default": 0},
		{"doctype": "Asset Shift Factor", "shift_name": "Single", "shift_factor": 1, "default": 1},
		{"doctype": "Asset Shift Factor", "shift_name": "Double", "shift_factor": 1.5, "default": 0},
		{"doctype": "Asset Shift Factor", "shift_name": "Triple", "shift_factor": 2, "default": 0},
	]

	for s in shifts:
		frappe.get_doc(s).insert()
