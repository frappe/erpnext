# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import cstr

from erpnext.assets.doctype.asset.test_asset import create_asset, create_asset_data
from erpnext.assets.doctype.asset_depreciation_schedule.asset_depreciation_schedule import (
	get_asset_depr_schedule_doc,
	get_depr_schedule,
)


class TestAssetDepreciationSchedule(FrappeTestCase):
	def setUp(self):
		create_asset_data()

	def test_throw_error_if_another_asset_depr_schedule_exist(self):
		asset = create_asset(item_code="Macbook Pro", calculate_depreciation=1, submit=1)

		first_asset_depr_schedule = get_asset_depr_schedule_doc(asset.name, "Active")
		self.assertEqual(first_asset_depr_schedule.status, "Active")

		second_asset_depr_schedule = frappe.get_doc(
			{"doctype": "Asset Depreciation Schedule", "asset": asset.name, "finance_book": None}
		)

		self.assertRaises(frappe.ValidationError, second_asset_depr_schedule.insert)

	def test_daily_prorata_based_depr_on_sl_methond(self):
		asset = create_asset(
			calculate_depreciation=1,
			depreciation_method="Straight Line",
			daily_prorata_based=1,
			available_for_use_date="2020-01-01",
			depreciation_start_date="2020-01-31",
			frequency_of_depreciation=1,
			total_number_of_depreciations=24,
		)

		expected_schedules = [
			["2020-01-31", 4234.97, 4234.97],
			["2020-02-29", 3961.75, 8196.72],
			["2020-03-31", 4234.97, 12431.69],
			["2020-04-30", 4098.36, 16530.05],
			["2020-05-31", 4234.97, 20765.02],
			["2020-06-30", 4098.36, 24863.38],
			["2020-07-31", 4234.97, 29098.35],
			["2020-08-31", 4234.97, 33333.32],
			["2020-09-30", 4098.36, 37431.68],
			["2020-10-31", 4234.97, 41666.65],
			["2020-11-30", 4098.36, 45765.01],
			["2020-12-31", 4234.97, 49999.98],
			["2021-01-31", 4246.58, 54246.56],
			["2021-02-28", 3835.62, 58082.18],
			["2021-03-31", 4246.58, 62328.76],
			["2021-04-30", 4109.59, 66438.35],
			["2021-05-31", 4246.58, 70684.93],
			["2021-06-30", 4109.59, 74794.52],
			["2021-07-31", 4246.58, 79041.1],
			["2021-08-31", 4246.58, 83287.68],
			["2021-09-30", 4109.59, 87397.27],
			["2021-10-31", 4246.58, 91643.85],
			["2021-11-30", 4109.59, 95753.44],
			["2021-12-31", 4246.56, 100000.0],
		]

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Draft")
		]
		self.assertEqual(schedules, expected_schedules)
	# Test for Written Down Value Method
	def test_daily_prorata_based_depreciation_for_wdv_method(self):
		# Frequency of deprciation = 3
		asset = create_asset(
			item_code="Macbook Pro",
			calculate_depreciation=1,
			depreciation_method="Written Down Value",
			daily_prorata_based=1,
			available_for_use_date="2021-02-20",
			depreciation_start_date="2021-03-31",
			frequency_of_depreciation=3,
			total_number_of_depreciations=18,
			rate_of_depreciation=40,
			submit=1,
		)
		asset_depr_schedule = frappe.get_last_doc("Asset Depreciation Schedule", {"asset": asset.name})
		self.assertEqual(asset_depr_schedule.depreciation_schedule[1].depreciation_amount, 9521.45)

		# Frequency of deprciation = 6
		asset = create_asset(
			item_code="Macbook Pro",
			calculate_depreciation=1,
			depreciation_method="Written Down Value",
			daily_prorata_based=1,
			available_for_use_date="2020-02-20",
			depreciation_start_date="2020-03-01",
			frequency_of_depreciation=6,
			total_number_of_depreciations=18,
			rate_of_depreciation=40,
			submit=1,
		)
		asset_depr_schedule = frappe.get_last_doc("Asset Depreciation Schedule", {"asset": asset.name})
		self.assertEqual(asset_depr_schedule.depreciation_schedule[1].depreciation_amount, 19889.52)

		# Frequency of deprciation = 12
		asset = create_asset(
			item_code="Macbook Pro",
			calculate_depreciation=1,
			depreciation_method="Written Down Value",
			daily_prorata_based=1,
			available_for_use_date="2020-02-20",
			depreciation_start_date="2020-03-01",
			frequency_of_depreciation=12,
			total_number_of_depreciations=4,
			rate_of_depreciation=40,
			submit=1,
		)
		asset_depr_schedule = frappe.get_last_doc("Asset Depreciation Schedule", {"asset": asset.name})
		self.assertEqual(asset_depr_schedule.depreciation_schedule[0].depreciation_amount, 1092.90)

	# Test for Straight Line Method
	def test_daily_prorata_based_depreciation_for_straight_line_method(self):
		asset = create_asset(
			item_code="Macbook Pro",
			calculate_depreciation=1,
			depreciation_method="Straight Line",
			daily_prorata_based=0,
			available_for_use_date="2020-02-20",
			depreciation_start_date="2020-03-01",
			frequency_of_depreciation=12,
			total_number_of_depreciations=4,
			submit=1,
		)
		asset_depr_schedule = frappe.get_last_doc("Asset Depreciation Schedule", {"asset": asset.name})
		self.assertEqual(asset_depr_schedule.depreciation_schedule[0].depreciation_amount, 751.37)
