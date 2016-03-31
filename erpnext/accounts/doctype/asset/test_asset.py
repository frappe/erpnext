# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import cstr
from erpnext.accounts.doctype.asset.depreciation import post_depreciation_entries, scrap_asset, restore_asset
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice

class TestAsset(unittest.TestCase):
	def setUp(self):
		set_depreciation_settings_in_company()
		create_asset()

	def test_fixed_asset_must_be_non_stock_item(self):
		item = frappe.get_doc("Item", "Macbook Pro")
		item.is_stock_item = 1
		self.assertRaises(frappe.ValidationError, item.save)

	def test_schedule_for_straight_line_method(self):
		asset = frappe.get_doc("Asset", "Macbook Pro 1")

		self.assertEqual(asset.status, "Draft")

		expected_schedules = [
			["2015-12-31", 30000, 30000],
			["2016-03-31", 30000, 60000],
			["2016-06-30", 30000, 90000]
		]

		schedules = [[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in asset.get("schedules")]

		self.assertEqual(schedules, expected_schedules)


	def test_schedule_for_double_declining_method(self):
		asset = frappe.get_doc("Asset", "Macbook Pro 1")
		asset.depreciation_method = "Double Declining Balance"
		asset.save()

		expected_schedules = [
			["2015-12-31", 66667, 66667],
			["2016-03-31", 22222, 88889],
			["2016-06-30", 1111, 90000]
		]

		schedules = [[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in asset.get("schedules")]

		self.assertEqual(schedules, expected_schedules)

	def test_depreciation(self):
		asset = frappe.get_doc("Asset", "Macbook Pro 1")
		asset.submit()
		asset.load_from_db()
		self.assertEqual(asset.status, "Submitted")

		post_depreciation_entries(date="2016-01-01")
		asset.load_from_db()

		self.assertEqual(asset.status, "Partially Depreciated")

		expected_gle = (
			("_Test Accumulated Depreciations - _TC", 0.0, 30000.0),
			("_Test Depreciations - _TC", 30000.0, 0.0)
		)

		gle = frappe.db.sql("""select account, debit, credit from `tabGL Entry`
			where against_voucher_type='Asset' and against_voucher = %s
			order by account""", asset.name)

		self.assertEqual(gle, expected_gle)
		self.assertEqual(asset.get("current_value"), 70000)


	def test_scrap_asset(self):
		asset = frappe.get_doc("Asset", "Macbook Pro 1")
		asset.submit()
		post_depreciation_entries(date="2016-01-01")

		scrap_asset("Macbook Pro 1")

		asset.load_from_db()
		self.assertEqual(asset.status, "Scrapped")
		self.assertTrue(asset.journal_entry_for_scrap)

		expected_gle = (
			("_Test Accumulated Depreciations - _TC", 30000.0, 0.0),
			("_Test Fixed Asset - _TC", 0.0, 100000.0),
			("_Test Gain/Loss on Asset Disposal - _TC", 70000.0, 0.0)
		)

		gle = frappe.db.sql("""select account, debit, credit from `tabGL Entry`
			where voucher_type='Journal Entry' and voucher_no = %s
			order by account""", asset.journal_entry_for_scrap)

		self.assertEqual(gle, expected_gle)

		restore_asset("Macbook Pro 1")

		asset.load_from_db()
		self.assertFalse(asset.journal_entry_for_scrap)
		self.assertEqual(asset.status, "Partially Depreciated")

	def test_asset_sale(self):
		frappe.get_doc("Asset", "Macbook Pro 1").submit()
		post_depreciation_entries(date="2016-01-01")

		si = create_sales_invoice(item_code="Macbook Pro", rate=25000, do_not_save=True)
		si.get("items")[0].asset = "Macbook Pro 1"
		si.submit()

		self.assertEqual(frappe.db.get_value("Asset", "Macbook Pro 1", "status"), "Sold")

		expected_gle = (
			("_Test Accumulated Depreciations - _TC", 30000.0, 0.0),
			("_Test Fixed Asset - _TC", 0.0, 100000.0),
			("_Test Gain/Loss on Asset Disposal - _TC", 45000.0, 0.0),
			("Debtors - _TC", 25000.0, 0.0)
		)

		gle = frappe.db.sql("""select account, debit, credit from `tabGL Entry`
			where voucher_type='Sales Invoice' and voucher_no = %s
			order by account""", si.name)

		self.assertEqual(gle, expected_gle)

		si.cancel()

		self.assertEqual(frappe.db.get_value("Asset", "Macbook Pro 1", "status"), "Partially Depreciated")

	def tearDown(self):
		asset = frappe.get_doc("Asset", "Macbook Pro 1")

		if asset.docstatus == 1 and asset.status not in ("Scrapped", "Sold", "Draft", "Cancelled"):
			asset.cancel()

			self.assertEqual(frappe.db.get_value("Asset", "Macbook Pro 1", "status"), "Cancelled")

		frappe.delete_doc("Asset", "Macbook Pro 1")

def create_asset():
	if not frappe.db.exists("Asset Category", "Computers"):
		create_asset_category()

	if not frappe.db.exists("Item", "Macbook Pro"):
		create_fixed_asset_item()

	asset = frappe.get_doc({
		"doctype": "Asset",
		"asset_name": "Macbook Pro 1",
		"asset_category": "Computers",
		"item_code": "Macbook Pro",
		"company": "_Test Company",
		"purchase_date": "2015-01-01",
		"next_depreciation_date": "2015-12-31",
		"gross_purchase_amount": 100000,
		"expected_value_after_useful_life": 10000
	})
	try:
		asset.save()
	except frappe.DuplicateEntryError:
		pass

	return asset

def create_asset_category():
	asset_category = frappe.new_doc("Asset Category")
	asset_category.asset_category_name = "Computers"
	asset_category.number_of_depreciations = 3
	asset_category.number_of_months_in_a_period = 3
	asset_category.append("accounts", {
		"company": "_Test Company",
		"fixed_asset_account": "_Test Fixed Asset - _TC",
		"accumulated_depreciation_account": "_Test Accumulated Depreciations - _TC",
		"depreciation_expense_account": "_Test Depreciations - _TC"
	})
	asset_category.insert()

def create_fixed_asset_item():
	try:
		frappe.get_doc({
			"doctype": "Item",
			"item_code": "Macbook Pro",
			"item_name": "Macbook Pro",
			"description": "Macbook Pro Retina Display",
			"item_group": "All Item Groups",
			"stock_uom": "Nos",
			"is_stock_item": 0
		}).insert()
	except frappe.DuplicateEntryError:
		pass

def set_depreciation_settings_in_company():
	company = frappe.get_doc("Company", "_Test Company")
	company.accumulated_depreciation_account = "_Test Accumulated Depreciations - _TC"
	company.depreciation_expense_account = "_Test Depreciations - _TC"
	company.disposal_account = "_Test Gain/Loss on Asset Disposal - _TC"
	company.depreciation_cost_center = "_Test Cost Center - _TC"
	company.save()