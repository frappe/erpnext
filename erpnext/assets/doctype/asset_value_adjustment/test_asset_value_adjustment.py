# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, cstr, get_last_day, getdate, nowdate

from erpnext.assets.doctype.asset.asset import get_asset_value_after_depreciation
from erpnext.assets.doctype.asset.depreciation import post_depreciation_entries
from erpnext.assets.doctype.asset_depreciation_schedule.asset_depreciation_schedule import (
	get_asset_depr_schedule_doc,
)
from erpnext.assets.doctype.asset_repair.test_asset_repair import create_asset_repair
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.tests.utils import ERPNextTestSuite


class TestAssetValueAdjustment(ERPNextTestSuite):
	def setUp(self):
		frappe.db.set_value(
			"Company", "_Test Company", "capital_work_in_progress_account", "CWIP Account - _TC"
		)

	def test_current_asset_value(self):
		pr = make_purchase_receipt(item_code="Macbook Pro", qty=1, rate=100000.0, location="Test Location")

		asset_name = frappe.db.get_value("Asset", {"purchase_receipt": pr.name}, "name")
		asset_doc = frappe.get_doc("Asset", asset_name)

		month_end_date = get_last_day(nowdate())
		purchase_date = nowdate() if nowdate() != month_end_date else add_days(nowdate(), -15)

		asset_doc.available_for_use_date = purchase_date
		asset_doc.purchase_date = purchase_date
		asset_doc.calculate_depreciation = 1
		asset_doc.append(
			"finance_books",
			{
				"expected_value_after_useful_life": 200,
				"depreciation_method": "Straight Line",
				"total_number_of_depreciations": 3,
				"frequency_of_depreciation": 10,
				"depreciation_start_date": month_end_date,
			},
		)
		asset_doc.submit()

		current_value = get_asset_value_after_depreciation(asset_doc.name)
		self.assertEqual(current_value, 100000.0)

	def test_asset_depreciation_value_adjustment(self):
		pr = make_purchase_receipt(item_code="Macbook Pro", qty=1, rate=120000.0, location="Test Location")

		asset_name = frappe.db.get_value("Asset", {"purchase_receipt": pr.name}, "name")
		asset_doc = frappe.get_doc("Asset", asset_name)
		asset_doc.calculate_depreciation = 1
		asset_doc.available_for_use_date = "2023-01-15"
		asset_doc.purchase_date = "2023-01-15"

		asset_doc.append(
			"finance_books",
			{
				"expected_value_after_useful_life": 200,
				"depreciation_method": "Straight Line",
				"total_number_of_depreciations": 12,
				"frequency_of_depreciation": 1,
				"depreciation_start_date": "2023-01-31",
			},
		)
		asset_doc.submit()

		first_asset_depr_schedule = get_asset_depr_schedule_doc(asset_doc.name, "Active")
		self.assertEqual(first_asset_depr_schedule.status, "Active")

		post_depreciation_entries(getdate("2023-08-21"))

		current_value = get_asset_value_after_depreciation(asset_doc.name)

		adj_doc = make_asset_value_adjustment(
			asset=asset_doc.name,
			current_asset_value=current_value,
			new_asset_value=50000.0,
			date="2023-08-21",
		)
		adj_doc.submit()

		first_asset_depr_schedule.load_from_db()

		second_asset_depr_schedule = get_asset_depr_schedule_doc(asset_doc.name, "Active")
		self.assertEqual(second_asset_depr_schedule.status, "Active")
		self.assertEqual(first_asset_depr_schedule.status, "Cancelled")

		expected_gle = (
			("_Test Difference Account - _TC", 4625.29, 0.0),
			("_Test Fixed Asset - _TC", 0.0, 4625.29),
		)

		gle = frappe.get_all(
			"GL Entry",
			filters={"voucher_type": "Journal Entry", "voucher_no": adj_doc.journal_entry},
			fields=["account", "debit", "credit"],
			order_by="account",
			as_list=True,
		)

		self.assertSequenceEqual(gle, expected_gle)

		expected_schedules = [
			["2023-01-31", 5474.73, 5474.73],
			["2023-02-28", 9983.33, 15458.06],
			["2023-03-31", 9983.33, 25441.39],
			["2023-04-30", 9983.33, 35424.72],
			["2023-05-31", 9983.33, 45408.05],
			["2023-06-30", 9983.33, 55391.38],
			["2023-07-31", 9983.33, 65374.71],
			["2023-08-31", 9134.91, 74509.62],
			["2023-09-30", 9134.91, 83644.53],
			["2023-10-31", 9134.91, 92779.44],
			["2023-11-30", 9134.91, 101914.35],
			["2023-12-31", 9134.91, 111049.26],
			["2024-01-15", 4125.45, 115174.71],
		]

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in second_asset_depr_schedule.get("depreciation_schedule")
		]

		self.assertEqual(schedules, expected_schedules)

	def test_depreciation_after_cancelling_asset_repair(self):
		pr = make_purchase_receipt(item_code="Macbook Pro", qty=1, rate=120000.0, location="Test Location")

		asset_name = frappe.db.get_value("Asset", {"purchase_receipt": pr.name}, "name")
		asset_doc = frappe.get_doc("Asset", asset_name)
		asset_doc.calculate_depreciation = 1
		asset_doc.available_for_use_date = "2023-01-15"
		asset_doc.purchase_date = "2023-01-15"

		asset_doc.append(
			"finance_books",
			{
				"expected_value_after_useful_life": 200,
				"depreciation_method": "Straight Line",
				"total_number_of_depreciations": 12,
				"frequency_of_depreciation": 1,
				"depreciation_start_date": "2023-01-31",
			},
		)
		asset_doc.submit()

		post_depreciation_entries(getdate("2023-08-21"))

		# create asset repair
		asset_repair = create_asset_repair(
			asset=asset_doc,
			capitalize_repair_cost=1,
			item="_Test Non Stock Item",
			submit=1,
			increase_in_asset_life=1,
		)

		first_asset_depr_schedule = get_asset_depr_schedule_doc(asset_doc.name, "Active")
		self.assertEqual(first_asset_depr_schedule.status, "Active")

		# create asset value adjustment
		current_value = get_asset_value_after_depreciation(asset_doc.name)

		adj_doc = make_asset_value_adjustment(
			asset=asset_doc.name,
			current_asset_value=current_value,
			new_asset_value=50000.0,
			date="2023-08-21",
		)
		adj_doc.submit()

		first_asset_depr_schedule.load_from_db()

		second_asset_depr_schedule = get_asset_depr_schedule_doc(asset_doc.name, "Active")
		self.assertEqual(second_asset_depr_schedule.status, "Active")
		self.assertEqual(first_asset_depr_schedule.status, "Cancelled")

		# Test gl entry creted from asset value adjustemnet
		expected_gle = (
			("_Test Difference Account - _TC", 5175.29, 0.0),
			("_Test Fixed Asset - _TC", 0.0, 5175.29),
		)

		gle = frappe.get_all(
			"GL Entry",
			filters={"voucher_type": "Journal Entry", "voucher_no": adj_doc.journal_entry},
			fields=["account", "debit", "credit"],
			order_by="account",
			as_list=True,
		)

		self.assertSequenceEqual(gle, expected_gle)

		# test depreciation schedule after asset repair and asset value adjustemnet
		expected_schedules = [
			["2023-01-31", 5474.73, 5474.73],
			["2023-02-28", 9983.33, 15458.06],
			["2023-03-31", 9983.33, 25441.39],
			["2023-04-30", 9983.33, 35424.72],
			["2023-05-31", 9983.33, 45408.05],
			["2023-06-30", 9983.33, 55391.38],
			["2023-07-31", 9983.33, 65374.71],
			["2023-08-31", 2853.6, 68228.31],
			["2023-09-30", 2853.6, 71081.91],
			["2023-10-31", 2853.6, 73935.51],
			["2023-11-30", 2853.6, 76789.11],
			["2023-12-31", 2853.6, 79642.71],
			["2024-01-31", 2853.6, 82496.31],
			["2024-02-29", 2853.6, 85349.91],
			["2024-03-31", 2853.6, 88203.51],
			["2024-04-30", 2853.6, 91057.11],
			["2024-05-31", 2853.6, 93910.71],
			["2024-06-30", 2853.6, 96764.31],
			["2024-07-31", 2853.6, 99617.91],
			["2024-08-31", 2853.6, 102471.51],
			["2024-09-30", 2853.6, 105325.11],
			["2024-10-31", 2853.6, 108178.71],
			["2024-11-30", 2853.6, 111032.31],
			["2024-12-31", 2853.6, 113885.91],
			["2025-01-31", 1288.8, 115174.71],
		]

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in second_asset_depr_schedule.get("depreciation_schedule")
		]

		self.assertEqual(schedules, expected_schedules)

		# Cancel asset repair
		asset_repair.cancel()
		asset_repair.load_from_db()
		second_asset_depr_schedule.load_from_db()

		third_asset_depr_schedule = get_asset_depr_schedule_doc(asset_doc.name, "Active")
		self.assertEqual(third_asset_depr_schedule.status, "Active")
		self.assertEqual(second_asset_depr_schedule.status, "Cancelled")

		# After cancelling asset repair asset life will be decreased and new depreciation schedule should be calculated
		expected_schedules = [
			["2023-01-31", 5474.73, 5474.73],
			["2023-02-28", 9983.33, 15458.06],
			["2023-03-31", 9983.33, 25441.39],
			["2023-04-30", 9983.33, 35424.72],
			["2023-05-31", 9983.33, 45408.05],
			["2023-06-30", 9983.33, 55391.38],
			["2023-07-31", 9983.33, 65374.71],
			["2023-08-31", 9034.02, 74408.73],
			["2023-09-30", 9034.02, 83442.75],
			["2023-10-31", 9034.02, 92476.77],
			["2023-11-30", 9034.02, 101510.79],
			["2023-12-31", 9034.02, 110544.81],
			["2024-01-15", 4079.9, 114624.71],
		]

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in third_asset_depr_schedule.get("depreciation_schedule")
		]

		self.assertEqual(schedules, expected_schedules)

	def test_difference_amount(self):
		pr = make_purchase_receipt(item_code="Macbook Pro", qty=1, rate=100000.0, location="Test Location")

		asset_name = frappe.db.get_value("Asset", {"purchase_receipt": pr.name}, "name")
		asset_doc = frappe.get_doc("Asset", asset_name)
		asset_doc.calculate_depreciation = 1
		asset_doc.available_for_use_date = "2023-01-15"
		asset_doc.purchase_date = "2023-01-15"

		asset_doc.append(
			"finance_books",
			{
				"expected_value_after_useful_life": 200,
				"depreciation_method": "Straight Line",
				"total_number_of_depreciations": 12,
				"frequency_of_depreciation": 1,
				"depreciation_start_date": "2023-01-31",
			},
		)
		asset_doc.submit()

		current_asset_value = get_asset_value_after_depreciation(asset_doc.name)
		adj_doc = make_asset_value_adjustment(
			asset=asset_doc.name,
			current_asset_value=current_asset_value,
			new_asset_value=40000,
			date="2023-08-21",
		)
		adj_doc.submit()
		difference_amount = adj_doc.new_asset_value - adj_doc.current_asset_value
		self.assertEqual(difference_amount, -60000)
		asset_doc.load_from_db()
		self.assertEqual(asset_doc.finance_books[0].value_after_depreciation, 40000.0)

	def test_expected_value_after_useful_life(self):
		pr = make_purchase_receipt(item_code="Macbook Pro", qty=1, rate=100000.0, location="Test Location")

		asset_name = frappe.db.get_value("Asset", {"purchase_receipt": pr.name}, "name")
		asset_doc = frappe.get_doc("Asset", asset_name)
		asset_doc.calculate_depreciation = 1
		asset_doc.available_for_use_date = "2023-01-15"
		asset_doc.purchase_date = "2023-01-15"

		asset_doc.append(
			"finance_books",
			{
				"expected_value_after_useful_life": 5000,
				"salvage_value_percentage": 5,
				"depreciation_method": "Straight Line",
				"total_number_of_depreciations": 12,
				"frequency_of_depreciation": 1,
				"depreciation_start_date": "2023-01-31",
			},
		)
		asset_doc.submit()
		self.assertEqual(asset_doc.finance_books[0].expected_value_after_useful_life, 5000.0)

		current_asset_value = get_asset_value_after_depreciation(asset_doc.name)
		adj_doc = make_asset_value_adjustment(
			asset=asset_doc.name,
			current_asset_value=current_asset_value,
			new_asset_value=40000,
			date="2023-08-21",
		)
		adj_doc.submit()
		difference_amount = adj_doc.new_asset_value - adj_doc.current_asset_value
		self.assertEqual(difference_amount, -60000)
		asset_doc.load_from_db()
		self.assertEqual(asset_doc.finance_books[0].value_after_depreciation, 40000.0)
		self.assertEqual(asset_doc.finance_books[0].expected_value_after_useful_life, 2000.0)


def make_asset_value_adjustment(**args):
	args = frappe._dict(args)

	doc = frappe.get_doc(
		{
			"doctype": "Asset Value Adjustment",
			"company": args.company or "_Test Company",
			"asset": args.asset,
			"date": args.date or nowdate(),
			"new_asset_value": args.new_asset_value,
			"current_asset_value": args.current_asset_value,
			"cost_center": args.cost_center or "Main - _TC",
			"difference_account": make_difference_account(),
		}
	).insert()

	return doc


def make_difference_account(**args):
	account = "_Test Difference Account - _TC"
	if not frappe.db.exists("Account", account):
		acc = frappe.new_doc("Account")
		acc.account_name = "_Test Difference Account"
		acc.parent_account = "Direct Income - _TC"
		acc.company = "_Test Company"
		acc.is_group = 0
		acc.insert()
		return acc.name
	else:
		return account
