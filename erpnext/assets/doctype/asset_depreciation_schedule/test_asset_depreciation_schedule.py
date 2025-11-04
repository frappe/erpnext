# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import cstr, date_diff, flt, getdate

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.assets.doctype.asset.depreciation import (
	post_depreciation_entries,
)
from erpnext.assets.doctype.asset.test_asset import create_asset, create_asset_data
from erpnext.assets.doctype.asset_depreciation_schedule.asset_depreciation_schedule import (
	get_asset_depr_schedule_doc,
	get_depr_schedule,
)
from erpnext.assets.doctype.asset_repair.test_asset_repair import create_asset_repair
from erpnext.assets.doctype.asset_value_adjustment.test_asset_value_adjustment import (
	make_asset_value_adjustment,
)


class TestAssetDepreciationSchedule(IntegrationTestCase):
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
		frappe.db.set_single_value("Accounts Settings", "calculate_depr_using_total_days", 0)
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

	def test_schedule_for_slm_for_existing_asset_daily_pro_rata_enabled(self):
		frappe.db.set_single_value("Accounts Settings", "calculate_depr_using_total_days", 1)
		asset = create_asset(
			calculate_depreciation=1,
			depreciation_method="Straight Line",
			available_for_use_date="2023-10-10",
			is_existing_asset=1,
			opening_number_of_booked_depreciations=9,
			opening_accumulated_depreciation=265,
			depreciation_start_date="2024-07-31",
			total_number_of_depreciations=24,
			frequency_of_depreciation=1,
			net_purchase_amount=731,
			daily_prorata_based=1,
		)

		expected_schedules = [
			["2024-07-31", 31.0, 296.0],
			["2024-08-31", 31.0, 327.0],
			["2024-09-30", 30.0, 357.0],
			["2024-10-31", 31.0, 388.0],
			["2024-11-30", 30.0, 418.0],
			["2024-12-31", 31.0, 449.0],
			["2025-01-31", 31.0, 480.0],
			["2025-02-28", 28.0, 508.0],
			["2025-03-31", 31.0, 539.0],
			["2025-04-30", 30.0, 569.0],
			["2025-05-31", 31.0, 600.0],
			["2025-06-30", 30.0, 630.0],
			["2025-07-31", 31.0, 661.0],
			["2025-08-31", 31.0, 692.0],
			["2025-09-30", 30.0, 722.0],
			["2025-10-10", 9.0, 731.0],
		]
		schedules = [
			[cstr(d.schedule_date), flt(d.depreciation_amount, 2), d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Draft")
		]
		self.assertEqual(schedules, expected_schedules)
		frappe.db.set_single_value("Accounts Settings", "calculate_depr_using_total_days", 0)

	def test_schedule_for_slm_for_existing_asset(self):
		asset = create_asset(
			calculate_depreciation=1,
			depreciation_method="Straight Line",
			available_for_use_date="2023-10-10",
			is_existing_asset=1,
			opening_number_of_booked_depreciations=9,
			opening_accumulated_depreciation=265.30,
			depreciation_start_date="2024-07-31",
			total_number_of_depreciations=24,
			frequency_of_depreciation=1,
			net_purchase_amount=731,
		)

		expected_schedules = [
			["2024-07-31", 30.46, 295.76],
			["2024-08-31", 30.46, 326.22],
			["2024-09-30", 30.46, 356.68],
			["2024-10-31", 30.46, 387.14],
			["2024-11-30", 30.46, 417.6],
			["2024-12-31", 30.46, 448.06],
			["2025-01-31", 30.46, 478.52],
			["2025-02-28", 30.46, 508.98],
			["2025-03-31", 30.46, 539.44],
			["2025-04-30", 30.46, 569.9],
			["2025-05-31", 30.46, 600.36],
			["2025-06-30", 30.46, 630.82],
			["2025-07-31", 30.46, 661.28],
			["2025-08-31", 30.46, 691.74],
			["2025-09-30", 30.46, 722.2],
			["2025-10-10", 8.8, 731.0],
		]
		schedules = [
			[cstr(d.schedule_date), flt(d.depreciation_amount, 2), d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Draft")
		]
		self.assertEqual(schedules, expected_schedules)

	def test_schedule_sl_method_for_existing_asset_with_frequency_of_3_months(self):
		asset = create_asset(
			calculate_depreciation=1,
			depreciation_method="Straight Line",
			available_for_use_date="2023-11-01",
			is_existing_asset=1,
			opening_number_of_booked_depreciations=4,
			opening_accumulated_depreciation=223.15,
			depreciation_start_date="2024-12-31",
			total_number_of_depreciations=12,
			frequency_of_depreciation=3,
			net_purchase_amount=731,
		)

		expected_schedules = [
			["2024-12-31", 60.98, 284.13],
			["2025-03-31", 60.98, 345.11],
			["2025-06-30", 60.98, 406.09],
			["2025-09-30", 60.98, 467.07],
			["2025-12-31", 60.98, 528.05],
			["2026-03-31", 60.98, 589.03],
			["2026-06-30", 60.98, 650.01],
			["2026-09-30", 60.98, 710.99],
			["2026-11-01", 20.01, 731.0],
		]
		schedules = [
			[cstr(d.schedule_date), flt(d.depreciation_amount, 2), d.accumulated_depreciation_amount]
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
			net_purchase_amount=1096,
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
			["2021-06-30", 9972.6, 14356.16],
			["2021-09-30", 10082.19, 24438.35],
			["2021-12-31", 10082.19, 34520.54],
			["2022-03-31", 6458.25, 40978.79],
			["2022-06-30", 6530.01, 47508.8],
			["2022-08-20", 52491.2, 100000.0],
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
			["2020-02-29", 1092.9, 1092.9],
			["2020-08-31", 20109.29, 21202.19],
			["2021-02-28", 15630.03, 36832.22],
			["2021-08-31", 15889.09, 52721.31],
			["2022-02-28", 9378.02, 62099.33],
			["2022-08-31", 9533.46, 71632.79],
			["2023-02-20", 28367.21, 100000.0],
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

	def test_depreciation_schedule_after_cancelling_asset_repair(self):
		asset = create_asset(
			item_code="Macbook Pro",
			net_purchase_amount=500,
			calculate_depreciation=1,
			depreciation_method="Straight Line",
			available_for_use_date="2023-01-01",
			depreciation_start_date="2023-01-31",
			frequency_of_depreciation=1,
			total_number_of_depreciations=12,
			submit=1,
		)

		expected_depreciation_before_repair = [
			["2023-01-31", 41.67, 41.67],
			["2023-02-28", 41.67, 83.34],
			["2023-03-31", 41.67, 125.01],
			["2023-04-30", 41.67, 166.68],
			["2023-05-31", 41.67, 208.35],
			["2023-06-30", 41.67, 250.02],
			["2023-07-31", 41.67, 291.69],
			["2023-08-31", 41.67, 333.36],
			["2023-09-30", 41.67, 375.03],
			["2023-10-31", 41.67, 416.7],
			["2023-11-30", 41.67, 458.37],
			["2023-12-31", 41.63, 500.0],
		]

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Active")
		]
		self.assertEqual(schedules, expected_depreciation_before_repair)
		self.assertEqual(asset.finance_books[0].value_after_depreciation, 500)

		asset_repair = create_asset_repair(
			asset=asset,
			capitalize_repair_cost=1,
			item="_Test Non Stock Item",
			failure_date="2023-04-01",
			pi_repair_cost1=60,
			pi_repair_cost2=40,
			increase_in_asset_life=0,
			submit=1,
		)
		self.assertEqual(asset_repair.total_repair_cost, 100)

		expected_depreciation_after_repair = [
			["2023-01-31", 50.0, 50.0],
			["2023-02-28", 50.0, 100.0],
			["2023-03-31", 50.0, 150.0],
			["2023-04-30", 50.0, 200.0],
			["2023-05-31", 50.0, 250.0],
			["2023-06-30", 50.0, 300.0],
			["2023-07-31", 50.0, 350.0],
			["2023-08-31", 50.0, 400.0],
			["2023-09-30", 50.0, 450.0],
			["2023-10-31", 50.0, 500.0],
			["2023-11-30", 50.0, 550.0],
			["2023-12-31", 50.0, 600.0],
		]

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Active")
		]
		self.assertEqual(schedules, expected_depreciation_after_repair)
		asset.reload()
		self.assertEqual(asset.finance_books[0].value_after_depreciation, 600)

		asset_repair.cancel()

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Active")
		]
		self.assertEqual(schedules, expected_depreciation_before_repair)
		asset.reload()
		self.assertEqual(asset.finance_books[0].value_after_depreciation, 500)

	def test_depreciation_schedule_after_cancelling_asset_repair_for_6_months_frequency(self):
		asset = create_asset(
			item_code="Macbook Pro",
			net_purchase_amount=500,
			calculate_depreciation=1,
			depreciation_method="Straight Line",
			available_for_use_date="2023-01-01",
			depreciation_start_date="2023-06-30",
			frequency_of_depreciation=6,
			total_number_of_depreciations=4,
			submit=1,
		)

		expected_depreciation_before_repair = [
			["2023-06-30", 125.0, 125.0],
			["2023-12-31", 125.0, 250.0],
			["2024-06-30", 125.0, 375.0],
			["2024-12-31", 125.0, 500.0],
		]

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Active")
		]

		self.assertEqual(schedules, expected_depreciation_before_repair)

		asset_repair = create_asset_repair(
			asset=asset,
			capitalize_repair_cost=1,
			item="_Test Non Stock Item",
			failure_date="2023-04-01",
			pi_repair_cost1=60,
			pi_repair_cost2=40,
			increase_in_asset_life=0,
			submit=1,
		)
		self.assertEqual(asset_repair.total_repair_cost, 100)

		expected_depreciation_after_repair = [
			["2023-06-30", 150.0, 150.0],
			["2023-12-31", 150.0, 300.0],
			["2024-06-30", 150.0, 450.0],
			["2024-12-31", 150.0, 600.0],
		]

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Active")
		]

		self.assertEqual(schedules, expected_depreciation_after_repair)
		asset.reload()
		self.assertEqual(asset.finance_books[0].value_after_depreciation, 600)

		asset_repair.cancel()

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Active")
		]
		self.assertEqual(schedules, expected_depreciation_before_repair)
		asset.reload()
		self.assertEqual(asset.finance_books[0].value_after_depreciation, 500)

	def test_depreciation_schedule_after_cancelling_asset_repair_for_existing_asset(self):
		asset = create_asset(
			item_code="Macbook Pro",
			net_purchase_amount=500,
			calculate_depreciation=1,
			depreciation_method="Straight Line",
			available_for_use_date="2023-01-15",
			depreciation_start_date="2023-03-31",
			frequency_of_depreciation=1,
			total_number_of_depreciations=12,
			is_existing_asset=1,
			opening_accumulated_depreciation=64.52,
			opening_number_of_booked_depreciations=2,
			submit=1,
		)

		expected_depreciation_before_repair = [
			["2023-03-31", 41.39, 105.91],
			["2023-04-30", 41.39, 147.3],
			["2023-05-31", 41.39, 188.69],
			["2023-06-30", 41.39, 230.08],
			["2023-07-31", 41.39, 271.47],
			["2023-08-31", 41.39, 312.86],
			["2023-09-30", 41.39, 354.25],
			["2023-10-31", 41.39, 395.64],
			["2023-11-30", 41.39, 437.03],
			["2023-12-31", 41.39, 478.42],
			["2024-01-15", 21.58, 500.0],
		]

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Active")
		]
		self.assertEqual(schedules, expected_depreciation_before_repair)

		asset_repair = create_asset_repair(
			asset=asset,
			capitalize_repair_cost=1,
			item="_Test Non Stock Item",
			failure_date="2023-04-01",
			pi_repair_cost1=60,
			pi_repair_cost2=40,
			increase_in_asset_life=0,
			submit=1,
		)
		self.assertEqual(asset_repair.total_repair_cost, 100)

		expected_depreciation_after_repair = [
			["2023-03-31", 50.9, 115.42],
			["2023-04-30", 50.9, 166.32],
			["2023-05-31", 50.9, 217.22],
			["2023-06-30", 50.9, 268.12],
			["2023-07-31", 50.9, 319.02],
			["2023-08-31", 50.9, 369.92],
			["2023-09-30", 50.9, 420.82],
			["2023-10-31", 50.9, 471.72],
			["2023-11-30", 50.9, 522.62],
			["2023-12-31", 50.9, 573.52],
			["2024-01-15", 26.48, 600.0],
		]

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Active")
		]
		self.assertEqual(schedules, expected_depreciation_after_repair)

		asset_repair.cancel()

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Active")
		]

		self.assertEqual(schedules, expected_depreciation_before_repair)
		asset.reload()
		self.assertEqual(asset.finance_books[0].value_after_depreciation, 435.48)

	def test_wdv_depreciation_schedule_after_cancelling_asset_repair(self):
		asset = create_asset(
			item_code="Macbook Pro",
			net_purchase_amount=500,
			calculate_depreciation=1,
			depreciation_method="Written Down Value",
			available_for_use_date="2023-04-01",
			depreciation_start_date="2023-12-31",
			frequency_of_depreciation=12,
			total_number_of_depreciations=4,
			rate_of_depreciation=40,
			submit=1,
		)

		expected_depreciation_before_repair = [
			["2023-12-31", 150.68, 150.68],
			["2024-12-31", 139.73, 290.41],
			["2025-12-31", 83.84, 374.25],
			["2026-12-31", 50.3, 424.55],
			["2027-04-01", 75.45, 500.0],
		]

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Active")
		]
		self.assertEqual(schedules, expected_depreciation_before_repair)

		asset_repair = create_asset_repair(
			asset=asset,
			capitalize_repair_cost=1,
			item="_Test Non Stock Item",
			failure_date="2024-01-01",
			pi_repair_cost1=60,
			pi_repair_cost2=40,
			increase_in_asset_life=0,
			submit=1,
		)

		expected_depreciation_after_repair = [
			["2023-12-31", 180.82, 180.82],
			["2024-12-31", 167.67, 348.49],
			["2025-12-31", 100.6, 449.09],
			["2026-12-31", 60.36, 509.45],
			["2027-04-01", 90.55, 600.0],
		]

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Active")
		]
		self.assertEqual(schedules, expected_depreciation_after_repair)

		asset_repair.cancel()
		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Active")
		]

		self.assertEqual(schedules, expected_depreciation_before_repair)

	def test_daily_prorata_based_depreciation_schedule_after_cancelling_asset_repair(self):
		asset = create_asset(
			item_code="Macbook Pro",
			net_purchase_amount=500,
			calculate_depreciation=1,
			depreciation_method="Straight Line",
			available_for_use_date="2023-01-01",
			depreciation_start_date="2023-01-31",
			daily_prorata_based=1,
			frequency_of_depreciation=1,
			total_number_of_depreciations=12,
			submit=1,
		)

		expected_depreciation_before_repair = [
			["2023-01-31", 42.47, 42.47],
			["2023-02-28", 38.36, 80.83],
			["2023-03-31", 42.47, 123.3],
			["2023-04-30", 41.1, 164.4],
			["2023-05-31", 42.47, 206.87],
			["2023-06-30", 41.1, 247.97],
			["2023-07-31", 42.47, 290.44],
			["2023-08-31", 42.47, 332.91],
			["2023-09-30", 41.1, 374.01],
			["2023-10-31", 42.47, 416.48],
			["2023-11-30", 41.1, 457.58],
			["2023-12-31", 42.42, 500.0],
		]

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Active")
		]
		self.assertEqual(schedules, expected_depreciation_before_repair)

		asset_repair = create_asset_repair(
			asset=asset,
			capitalize_repair_cost=1,
			item="_Test Non Stock Item",
			failure_date="2023-04-01",
			pi_repair_cost1=60,
			pi_repair_cost2=40,
			increase_in_asset_life=0,
			submit=1,
		)
		self.assertEqual(asset_repair.total_repair_cost, 100)

		expected_depreciation_after_repair = [
			["2023-01-31", 50.96, 50.96],
			["2023-02-28", 46.03, 96.99],
			["2023-03-31", 50.96, 147.95],
			["2023-04-30", 49.32, 197.27],
			["2023-05-31", 50.96, 248.23],
			["2023-06-30", 49.32, 297.55],
			["2023-07-31", 50.96, 348.51],
			["2023-08-31", 50.96, 399.47],
			["2023-09-30", 49.32, 448.79],
			["2023-10-31", 50.96, 499.75],
			["2023-11-30", 49.32, 549.07],
			["2023-12-31", 50.93, 600.0],
		]

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Active")
		]
		self.assertEqual(schedules, expected_depreciation_after_repair)
		asset.reload()
		self.assertEqual(asset.finance_books[0].value_after_depreciation, 600)

		asset_repair.cancel()

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Active")
		]
		self.assertEqual(schedules, expected_depreciation_before_repair)
		asset.reload()
		self.assertEqual(asset.finance_books[0].value_after_depreciation, 500)

	def test_depreciation_schedule_after_cancelling_asset_value_adjustent(self):
		asset = create_asset(
			item_code="Macbook Pro",
			net_purchase_amount=1000,
			calculate_depreciation=1,
			depreciation_method="Straight Line",
			available_for_use_date="2023-01-01",
			depreciation_start_date="2023-01-31",
			frequency_of_depreciation=1,
			total_number_of_depreciations=12,
			submit=1,
		)

		expected_depreciation_before_adjustment = [
			["2023-01-31", 83.33, 83.33],
			["2023-02-28", 83.33, 166.66],
			["2023-03-31", 83.33, 249.99],
			["2023-04-30", 83.33, 333.32],
			["2023-05-31", 83.33, 416.65],
			["2023-06-30", 83.33, 499.98],
			["2023-07-31", 83.33, 583.31],
			["2023-08-31", 83.33, 666.64],
			["2023-09-30", 83.33, 749.97],
			["2023-10-31", 83.33, 833.3],
			["2023-11-30", 83.33, 916.63],
			["2023-12-31", 83.37, 1000.0],
		]
		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Active")
		]
		self.assertEqual(schedules, expected_depreciation_before_adjustment)

		current_asset_value = asset.finance_books[0].value_after_depreciation
		asset_value_adjustment = make_asset_value_adjustment(
			asset=asset.name,
			date="2023-04-01",
			current_asset_value=current_asset_value,
			new_asset_value=1200,
		)
		asset_value_adjustment.submit()

		expected_depreciation_after_adjustment = [
			["2023-01-31", 100.0, 100.0],
			["2023-02-28", 100.0, 200.0],
			["2023-03-31", 100.0, 300.0],
			["2023-04-30", 100.0, 400.0],
			["2023-05-31", 100.0, 500.0],
			["2023-06-30", 100.0, 600.0],
			["2023-07-31", 100.0, 700.0],
			["2023-08-31", 100.0, 800.0],
			["2023-09-30", 100.0, 900.0],
			["2023-10-31", 100.0, 1000.0],
			["2023-11-30", 100.0, 1100.0],
			["2023-12-31", 100.0, 1200.0],
		]

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Active")
		]
		self.assertEqual(schedules, expected_depreciation_after_adjustment)

		asset_value_adjustment.cancel()
		asset.reload()
		self.assertEqual(asset.finance_books[0].value_after_depreciation, 1000)

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Active")
		]
		self.assertEqual(schedules, expected_depreciation_before_adjustment)

	def test_depreciation_on_return_of_sold_asset(self):
		from erpnext.controllers.sales_and_purchase_return import make_return_doc

		create_asset_data()
		asset = create_asset(item_code="Macbook Pro", calculate_depreciation=1, submit=1)
		post_depreciation_entries(getdate("2021-09-30"))

		si = create_sales_invoice(
			item_code="Macbook Pro", asset=asset.name, qty=1, rate=90000, posting_date=getdate("2021-09-30")
		)
		return_si = make_return_doc("Sales Invoice", si.name)
		return_si.submit()
		asset.load_from_db()

		expected_values = [
			["2020-06-30", 1366.12, 1366.12, True],
			["2021-06-30", 20000.0, 21366.12, True],
			["2022-06-30", 20000.95, 41367.07, False],
			["2023-06-30", 20000.95, 61368.02, False],
			["2024-06-30", 20000.95, 81368.97, False],
			["2025-06-06", 18631.03, 100000.0, False],
		]

		for i, schedule in enumerate(get_depr_schedule(asset.name, "Active")):
			self.assertEqual(getdate(expected_values[i][0]), schedule.schedule_date)
			self.assertEqual(expected_values[i][1], schedule.depreciation_amount)
			self.assertEqual(expected_values[i][2], schedule.accumulated_depreciation_amount)
			self.assertEqual(schedule.journal_entry, schedule.journal_entry)

	def test_depreciation_schedule_after_cancelling_asset_value_adjustent_for_existing_asset(self):
		asset = create_asset(
			item_code="Macbook Pro",
			net_purchase_amount=500,
			calculate_depreciation=1,
			depreciation_method="Straight Line",
			available_for_use_date="2023-01-15",
			depreciation_start_date="2023-03-31",
			frequency_of_depreciation=1,
			total_number_of_depreciations=12,
			is_existing_asset=1,
			opening_accumulated_depreciation=64.52,
			opening_number_of_booked_depreciations=2,
			submit=1,
		)

		expected_depreciation_before_adjustment = [
			["2023-03-31", 41.39, 105.91],
			["2023-04-30", 41.39, 147.3],
			["2023-05-31", 41.39, 188.69],
			["2023-06-30", 41.39, 230.08],
			["2023-07-31", 41.39, 271.47],
			["2023-08-31", 41.39, 312.86],
			["2023-09-30", 41.39, 354.25],
			["2023-10-31", 41.39, 395.64],
			["2023-11-30", 41.39, 437.03],
			["2023-12-31", 41.39, 478.42],
			["2024-01-15", 21.58, 500.0],
		]

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Active")
		]
		self.assertEqual(schedules, expected_depreciation_before_adjustment)

		current_asset_value = asset.finance_books[0].value_after_depreciation
		asset_value_adjustment = make_asset_value_adjustment(
			asset=asset.name,
			date="2023-04-01",
			current_asset_value=current_asset_value,
			new_asset_value=600,
		)
		asset_value_adjustment.submit()

		expected_depreciation_after_adjustment = [
			["2023-03-31", 57.03, 121.55],
			["2023-04-30", 57.03, 178.58],
			["2023-05-31", 57.03, 235.61],
			["2023-06-30", 57.03, 292.64],
			["2023-07-31", 57.03, 349.67],
			["2023-08-31", 57.03, 406.7],
			["2023-09-30", 57.03, 463.73],
			["2023-10-31", 57.03, 520.76],
			["2023-11-30", 57.03, 577.79],
			["2023-12-31", 57.03, 634.82],
			["2024-01-15", 29.7, 664.52],
		]

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Active")
		]
		self.assertEqual(schedules, expected_depreciation_after_adjustment)

		asset_value_adjustment.cancel()

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Active")
		]

		self.assertEqual(schedules, expected_depreciation_before_adjustment)

	def test_depreciation_schedule_for_parallel_adjustment_and_repair(self):
		asset = create_asset(
			item_code="Macbook Pro",
			net_purchase_amount=600,
			calculate_depreciation=1,
			depreciation_method="Straight Line",
			available_for_use_date="2021-01-01",
			depreciation_start_date="2021-12-31",
			frequency_of_depreciation=12,
			total_number_of_depreciations=3,
			is_existing_asset=1,
			submit=1,
		)
		post_depreciation_entries(date="2021-12-31")
		asset.reload()

		expected_depreciation_before_adjustment = [
			["2021-12-31", 200, 200],
			["2022-12-31", 200, 400],
			["2023-12-31", 200, 600],
		]

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Active")
		]
		self.assertEqual(schedules, expected_depreciation_before_adjustment)

		current_asset_value = asset.finance_books[0].value_after_depreciation
		asset_value_adjustment = make_asset_value_adjustment(
			asset=asset.name,
			date="2022-01-15",
			current_asset_value=current_asset_value,
			new_asset_value=500,
		)
		asset_value_adjustment.submit()

		expected_depreciation_after_adjustment = [
			["2021-12-31", 200, 200],
			["2022-12-31", 250, 450],
			["2023-12-31", 250, 700],
		]

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Active")
		]
		self.assertEqual(schedules, expected_depreciation_after_adjustment)

		asset_repair = create_asset_repair(
			asset=asset,
			capitalize_repair_cost=1,
			item="_Test Non Stock Item",
			failure_date="2022-01-20",
			pi_repair_cost1=60,
			pi_repair_cost2=40,
			increase_in_asset_life=0,
			submit=1,
		)
		self.assertEqual(asset_repair.total_repair_cost, 100)

		expected_depreciation_after_repair = [
			["2021-12-31", 200, 200],
			["2022-12-31", 300, 500],
			["2023-12-31", 300, 800],
		]

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Active")
		]
		self.assertEqual(schedules, expected_depreciation_after_repair)
		asset.reload()

		asset_value_adjustment.cancel()

		expected_depreciation_after_cancelling_adjustment = [
			["2021-12-31", 200, 200],
			["2022-12-31", 250, 450],
			["2023-12-31", 250, 700],
		]

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Active")
		]

		self.assertEqual(schedules, expected_depreciation_after_cancelling_adjustment)

	def test_depreciation_schedule_after_sale_of_asset(self):
		asset = create_asset(
			item_code="Macbook Pro",
			net_purchase_amount=600,
			calculate_depreciation=1,
			depreciation_method="Straight Line",
			available_for_use_date="2021-01-01",
			depreciation_start_date="2021-12-31",
			frequency_of_depreciation=12,
			total_number_of_depreciations=3,
			is_existing_asset=1,
			submit=1,
		)
		post_depreciation_entries(date="2021-12-31")
		asset.reload()

		expected_depreciation_before_adjustment = [
			["2021-12-31", 200, 200],
			["2022-12-31", 200, 400],
			["2023-12-31", 200, 600],
		]

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Active")
		]
		self.assertEqual(schedules, expected_depreciation_before_adjustment)

		current_asset_value = asset.finance_books[0].value_after_depreciation
		asset_value_adjustment = make_asset_value_adjustment(
			asset=asset.name,
			date="2022-01-15",
			current_asset_value=current_asset_value,
			new_asset_value=500,
		)
		asset_value_adjustment.submit()

		expected_depreciation_after_adjustment = [
			["2021-12-31", 200, 200],
			["2022-12-31", 250, 450],
			["2023-12-31", 250, 700],
		]

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Active")
		]
		self.assertEqual(schedules, expected_depreciation_after_adjustment)

		si = create_sales_invoice(
			item_code="Macbook Pro", asset=asset.name, qty=1, rate=300, posting_date=getdate("2022-04-01")
		)
		asset.load_from_db()

		self.assertEqual(frappe.db.get_value("Asset", asset.name, "status"), "Sold")

		expected_depreciation_after_sale = [
			["2021-12-31", 200.0, 200.0],
			["2022-04-01", 62.33, 262.33],
		]

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Active")
		]
		self.assertEqual(schedules, expected_depreciation_after_sale)

		si.cancel()
		asset.reload()

		self.assertEqual(frappe.db.get_value("Asset", asset.name, "status"), "Partially Depreciated")

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Active")
		]
		self.assertEqual(schedules, expected_depreciation_after_adjustment)

	def test_depreciation_schedule_after_sale_of_asset_wdv_method(self):
		asset = create_asset(
			item_code="Macbook Pro",
			net_purchase_amount=500,
			calculate_depreciation=1,
			depreciation_method="Written Down Value",
			available_for_use_date="2021-01-01",
			depreciation_start_date="2021-12-31",
			rate_of_depreciation=50,
			frequency_of_depreciation=12,
			total_number_of_depreciations=3,
			is_existing_asset=1,
			submit=1,
		)
		post_depreciation_entries(date="2021-12-31")
		asset.reload()

		expected_depreciation_before_repair = [
			["2021-12-31", 250.0, 250.0],
			["2022-12-31", 125.0, 375.0],
			["2023-12-31", 125.0, 500.0],
		]

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Active")
		]
		self.assertEqual(schedules, expected_depreciation_before_repair)

		create_asset_repair(
			asset=asset,
			capitalize_repair_cost=1,
			item="_Test Non Stock Item",
			failure_date="2022-03-01",
			pi_repair_cost1=60,
			pi_repair_cost2=40,
			increase_in_asset_life=0,
			submit=1,
		)

		expected_depreciation_after_repair = [
			["2021-12-31", 250.0, 250.0],
			["2022-12-31", 175.0, 425.0],
			["2023-12-31", 175.0, 600.0],
		]

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Active")
		]
		self.assertEqual(schedules, expected_depreciation_after_repair)

		si = create_sales_invoice(
			item_code="Macbook Pro", asset=asset.name, qty=1, rate=300, posting_date=getdate("2022-04-01")
		)
		asset.load_from_db()

		self.assertEqual(frappe.db.get_value("Asset", asset.name, "status"), "Sold")

		expected_depreciation_after_sale = [
			["2021-12-31", 250.0, 250.0],
			["2022-04-01", 43.63, 293.63],
		]

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Active")
		]
		self.assertEqual(schedules, expected_depreciation_after_sale)

		si.cancel()
		asset.reload()
		self.assertEqual(frappe.db.get_value("Asset", asset.name, "status"), "Partially Depreciated")

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Active")
		]
		self.assertEqual(schedules, expected_depreciation_after_repair)
