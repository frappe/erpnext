# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import add_days, cstr, get_last_day, getdate, nowdate

from erpnext.assets.doctype.asset.asset import get_asset_value_after_depreciation
from erpnext.assets.doctype.asset.depreciation import post_depreciation_entries
from erpnext.assets.doctype.asset.test_asset import create_asset_data
from erpnext.assets.doctype.asset_depreciation_schedule.asset_depreciation_schedule import (
	get_asset_depr_schedule_doc,
)
from erpnext.assets.doctype.asset_repair.test_asset_repair import create_asset_repair
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt


class TestAssetValueAdjustment(unittest.TestCase):
	def setUp(self):
		create_asset_data()
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
			("_Test Accumulated Depreciations - _TC", 0.0, 4625.29),
			("_Test Depreciations - _TC", 4625.29, 0.0),
		)

		gle = frappe.db.sql(
			"""select account, debit, credit from `tabGL Entry`
			where voucher_type='Journal Entry' and voucher_no = %s
			order by account""",
			adj_doc.journal_entry,
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
			["2023-08-31", 8300.0, 73674.71],
			["2023-09-30", 8300.0, 81974.71],
			["2023-10-31", 8300.0, 90274.71],
			["2023-11-30", 8300.0, 98574.71],
			["2023-12-31", 8300.0, 106874.71],
			["2024-01-15", 8300.0, 115174.71],
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
		asset_repair = create_asset_repair(asset=asset_doc, capitalize_repair_cost=1, submit=1)

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
			("_Test Accumulated Depreciations - _TC", 0.0, 5625.29),
			("_Test Depreciations - _TC", 5625.29, 0.0),
		)

		gle = frappe.db.sql(
			"""select account, debit, credit from `tabGL Entry`
			where voucher_type='Journal Entry' and voucher_no = %s
			order by account""",
			adj_doc.journal_entry,
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
			["2023-08-31", 2766.67, 68141.38],
			["2023-09-30", 2766.67, 70908.05],
			["2023-10-31", 2766.67, 73674.72],
			["2023-11-30", 2766.67, 76441.39],
			["2023-12-31", 2766.67, 79208.06],
			["2024-01-31", 2766.67, 81974.73],
			["2024-02-29", 2766.67, 84741.4],
			["2024-03-31", 2766.67, 87508.07],
			["2024-04-30", 2766.67, 90274.74],
			["2024-05-31", 2766.67, 93041.41],
			["2024-06-30", 2766.67, 95808.08],
			["2024-07-31", 2766.67, 98574.75],
			["2024-08-31", 2766.67, 101341.42],
			["2024-09-30", 2766.67, 104108.09],
			["2024-10-31", 2766.67, 106874.76],
			["2024-11-30", 2766.67, 109641.43],
			["2024-12-31", 2766.67, 112408.1],
			["2025-01-15", 2766.61, 115174.71],
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
			["2023-08-31", 8133.33, 73508.04],
			["2023-09-30", 8133.33, 81641.37],
			["2023-10-31", 8133.33, 89774.7],
			["2023-11-30", 8133.33, 97908.03],
			["2023-12-31", 8133.33, 106041.36],
			["2024-01-15", 8133.35, 114174.71],
		]

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in third_asset_depr_schedule.get("depreciation_schedule")
		]

		self.assertEqual(schedules, expected_schedules)


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
		}
	).insert()

	return doc
