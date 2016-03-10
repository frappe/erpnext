# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

class TestAsset(unittest.TestCase):
	def setUp(self):
		create_asset()
		
	def test_fixed_asset_must_be_non_stock_item(self):
		item = frappe.get_doc("Item", "Macbook Pro")
		item.is_stock_item = 1
		self.assertRaises(frappe.ValidationError, item.save)
	
	def test_asset_purchase(self):
		asset = create_asset()
		
		self.assertEqual(asset.current_value, 100000)


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
	asset_category.number_of_depreciations = 5
	asset_category.number_of_months_in_a_period = 12
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
			"is_fixed_asset": 1,
			"is_stock_item": 0
		}).insert()
	except frappe.DuplicateEntryError:
		pass
	
	