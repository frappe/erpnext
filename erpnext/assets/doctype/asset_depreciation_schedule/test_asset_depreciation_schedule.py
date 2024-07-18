# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import cstr, flt

from erpnext.assets.doctype.asset.depreciation import (
	post_depreciation_entries,
)
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

	def test_daily_prorata_based_depr_on_sl_method(self):
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

	# Enable Checkbox to Calculate depreciation using total days in depreciation period
	def test_daily_prorata_based_depr_after_enabling_configuration(self):
		frappe.db.set_single_value("Accounts Settings", "calculate_depr_using_total_days", 1)

		asset = create_asset(
			calculate_depreciation=1,
			depreciation_method="Straight Line",
			daily_prorata_based=1,
			gross_purchase_amount=1096,
			available_for_use_date="2020-01-15",
			depreciation_start_date="2020-01-31",
			frequency_of_depreciation=1,
			total_number_of_depreciations=36,
		)

		expected_schedule = [
			["2020-01-31", 17.0, 17.0],
			["2020-02-29", 29.0, 46.0],
			["2020-03-31", 31.0, 77.0],
			["2020-04-30", 30.0, 107.0],
			["2020-05-31", 31.0, 138.0],
			["2020-06-30", 30.0, 168.0],
			["2020-07-31", 31.0, 199.0],
			["2020-08-31", 31.0, 230.0],
			["2020-09-30", 30.0, 260.0],
			["2020-10-31", 31.0, 291.0],
			["2020-11-30", 30.0, 321.0],
			["2020-12-31", 31.0, 352.0],
			["2021-01-31", 31.0, 383.0],
			["2021-02-28", 28.0, 411.0],
			["2021-03-31", 31.0, 442.0],
			["2021-04-30", 30.0, 472.0],
			["2021-05-31", 31.0, 503.0],
			["2021-06-30", 30.0, 533.0],
			["2021-07-31", 31.0, 564.0],
			["2021-08-31", 31.0, 595.0],
			["2021-09-30", 30.0, 625.0],
			["2021-10-31", 31.0, 656.0],
			["2021-11-30", 30.0, 686.0],
			["2021-12-31", 31.0, 717.0],
			["2022-01-31", 31.0, 748.0],
			["2022-02-28", 28.0, 776.0],
			["2022-03-31", 31.0, 807.0],
			["2022-04-30", 30.0, 837.0],
			["2022-05-31", 31.0, 868.0],
			["2022-06-30", 30.0, 898.0],
			["2022-07-31", 31.0, 929.0],
			["2022-08-31", 31.0, 960.0],
			["2022-09-30", 30.0, 990.0],
			["2022-10-31", 31.0, 1021.0],
			["2022-11-30", 30.0, 1051.0],
			["2022-12-31", 31.0, 1082.0],
			["2023-01-15", 14.0, 1096.0],
		]

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Draft")
		]
		self.assertEqual(schedules, expected_schedule)
		frappe.db.set_single_value("Accounts Settings", "calculate_depr_using_total_days", 0)

	# Test for Written Down Value Method
	# Frequency of deprciation = 3
	def test_for_daily_prorata_based_depreciation_wdv_method_frequency_3_months(self):
		asset = create_asset(
			item_code="Macbook Pro",
			calculate_depreciation=1,
			depreciation_method="Written Down Value",
			daily_prorata_based=1,
			available_for_use_date="2021-02-20",
			depreciation_start_date="2021-03-31",
			frequency_of_depreciation=3,
			total_number_of_depreciations=6,
			rate_of_depreciation=40,
		)

		expected_schedules = [
			["2021-03-31", 4383.56, 4383.56],
			["2021-06-30", 9535.45, 13919.01],
			["2021-09-30", 9640.23, 23559.24],
			["2021-12-31", 9640.23, 33199.47],
			["2022-03-31", 9430.66, 42630.13],
			["2022-06-30", 5721.27, 48351.4],
			["2022-08-20", 51648.6, 100000.0],
		]

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Draft")
		]
		self.assertEqual(schedules, expected_schedules)

	# Frequency of deprciation = 6
	def test_for_daily_prorata_based_depreciation_wdv_method_frequency_6_months(self):
		asset = create_asset(
			item_code="Macbook Pro",
			calculate_depreciation=1,
			depreciation_method="Written Down Value",
			daily_prorata_based=1,
			available_for_use_date="2020-02-20",
			depreciation_start_date="2020-02-29",
			frequency_of_depreciation=6,
			total_number_of_depreciations=6,
			rate_of_depreciation=40,
		)

		expected_schedules = [
			["2020-02-29", 1092.90, 1092.90],
			["2020-08-31", 19944.01, 21036.91],
			["2021-02-28", 19618.83, 40655.74],
			["2021-08-31", 11966.4, 52622.14],
			["2022-02-28", 11771.3, 64393.44],
			["2022-08-31", 7179.84, 71573.28],
			["2023-02-20", 28426.72, 100000.0],
		]

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Draft")
		]
		self.assertEqual(schedules, expected_schedules)

	# Frequency of deprciation = 12
	def test_for_daily_prorata_based_depreciation_wdv_method_frequency_12_months(self):
		asset = create_asset(
			item_code="Macbook Pro",
			calculate_depreciation=1,
			depreciation_method="Written Down Value",
			daily_prorata_based=1,
			available_for_use_date="2020-02-20",
			depreciation_start_date="2020-03-31",
			frequency_of_depreciation=12,
			total_number_of_depreciations=4,
			rate_of_depreciation=40,
		)

		expected_schedules = [
			["2020-03-31", 4480.87, 4480.87],
			["2021-03-31", 38207.65, 42688.52],
			["2022-03-31", 22924.59, 65613.11],
			["2023-03-31", 13754.76, 79367.87],
			["2024-02-20", 20632.13, 100000],
		]

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Draft")
		]
		self.assertEqual(schedules, expected_schedules)

	def test_update_total_number_of_booked_depreciations(self):
		# check if updates total number of booked depreciations when depreciation gets booked
		asset = create_asset(
			item_code="Macbook Pro",
			calculate_depreciation=1,
			opening_accumulated_depreciation=2000,
			opening_number_of_booked_depreciations=2,
			depreciation_method="Straight Line",
			available_for_use_date="2020-01-01",
			depreciation_start_date="2020-03-31",
			frequency_of_depreciation=1,
			total_number_of_depreciations=24,
			submit=1,
		)

		post_depreciation_entries(date="2021-03-31")
		asset.reload()
		"""
		opening_number_of_booked_depreciations = 2
		number_of_booked_depreciations till 2021-03-31 = 13
		total_number_of_booked_depreciations = 15
		"""
		self.assertEqual(asset.finance_books[0].total_number_of_booked_depreciations, 15)

		# cancel depreciation entry
		depr_entry = get_depr_schedule(asset.name, "Active")[0].journal_entry

		frappe.get_doc("Journal Entry", depr_entry).cancel()
		asset.reload()

		self.assertEqual(asset.finance_books[0].total_number_of_booked_depreciations, 14)

	def test_schedule_for_wdv_method_for_existing_asset(self):
		asset = create_asset(
			calculate_depreciation=1,
			depreciation_method="Written Down Value",
			available_for_use_date="2020-07-17",
			is_existing_asset=1,
			opening_number_of_booked_depreciations=2,
			opening_accumulated_depreciation=11666.67,
			depreciation_start_date="2021-04-30",
			total_number_of_depreciations=12,
			frequency_of_depreciation=3,
			gross_purchase_amount=50000,
			rate_of_depreciation=40,
		)

		self.assertEqual(asset.status, "Draft")
		expected_schedules = [
			["2021-04-30", 3833.33, 15500.0],
			["2021-07-31", 3833.33, 19333.33],
			["2021-10-31", 3833.33, 23166.66],
			["2022-01-31", 3833.33, 26999.99],
			["2022-04-30", 2300.0, 29299.99],
			["2022-07-31", 2300.0, 31599.99],
			["2022-10-31", 2300.0, 33899.99],
			["2023-01-31", 2300.0, 36199.99],
			["2023-04-30", 1380.0, 37579.99],
			["2023-07-31", 12420.01, 50000.0],
		]
		schedules = [
			[cstr(d.schedule_date), flt(d.depreciation_amount, 2), d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Draft")
		]
		self.assertEqual(schedules, expected_schedules)
