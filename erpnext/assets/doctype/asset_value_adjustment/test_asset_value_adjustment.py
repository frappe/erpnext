# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import add_days, get_last_day, nowdate

from erpnext.assets.doctype.asset.asset import get_asset_value_after_depreciation
from erpnext.assets.doctype.asset.test_asset import create_asset_data
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt


class TestAssetValueAdjustment(unittest.TestCase):
	def setUp(self):
		create_asset_data()

	def test_current_asset_value(self):
		pr = make_purchase_receipt(
			item_code="Macbook Pro", qty=1, rate=100000.0, location="Test Location"
		)

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
		pr = make_purchase_receipt(
			item_code="Macbook Pro", qty=1, rate=100000.0, location="Test Location"
		)

		asset_name = frappe.db.get_value("Asset", {"purchase_receipt": pr.name}, "name")
		asset_doc = frappe.get_doc("Asset", asset_name)
		asset_doc.calculate_depreciation = 1

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
		adj_doc = make_asset_value_adjustment(
			asset=asset_doc.name, current_asset_value=current_value, new_asset_value=50000.0
		)
		adj_doc.submit()

		expected_gle = (
			("_Test Accumulated Depreciations - _TC", 0.0, 50000.0),
			("_Test Depreciations - _TC", 50000.0, 0.0),
		)

		gle = frappe.db.sql(
			"""select account, debit, credit from `tabGL Entry`
			where voucher_type='Journal Entry' and voucher_no = %s
			order by account""",
			adj_doc.journal_entry,
		)

		self.assertSequenceEqual(gle, expected_gle)


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
