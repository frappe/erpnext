# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe

from erpnext.assets.doctype.asset.test_asset import create_asset


class TestAssetCategory(unittest.TestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_mandatory_fields(self):
		asset_category = frappe.new_doc("Asset Category")
		asset_category.asset_category_name = "Computers"

		self.assertRaises(frappe.MandatoryError, asset_category.insert)

		asset_category.total_number_of_depreciations = 3
		asset_category.frequency_of_depreciation = 3
		asset_category.append(
			"accounts",
			{
				"company_name": "_Test Company",
				"fixed_asset_account": "_Test Fixed Asset - _TC",
				"accumulated_depreciation_account": "_Test Accumulated Depreciations - _TC",
				"depreciation_expense_account": "_Test Depreciations - _TC",
			},
		)

		try:
			asset_category.insert(ignore_if_duplicate=True)
		except frappe.DuplicateEntryError:
			pass

	def test_cwip_accounting(self):
		frappe.db.get_value("Company", "_Test Company", "capital_work_in_progress_account")
		frappe.db.set_value("Company", "_Test Company", "capital_work_in_progress_account", "")

		asset_category = frappe.new_doc("Asset Category")
		asset_category.asset_category_name = "Computers"
		asset_category.enable_cwip_accounting = 1

		asset_category.total_number_of_depreciations = 3
		asset_category.frequency_of_depreciation = 3
		asset_category.append(
			"accounts",
			{
				"company_name": "_Test Company",
				"fixed_asset_account": "_Test Fixed Asset - _TC",
				"accumulated_depreciation_account": "_Test Accumulated Depreciations - _TC",
				"depreciation_expense_account": "_Test Depreciations - _TC",
			},
		)

		self.assertRaises(frappe.ValidationError, asset_category.insert)

	def test_accounts_cannot_change_while_active_assets_exist(self):
		asset = create_asset(asset_category="Computers", company="_Test Company", submit=1)
		asset_category = frappe.get_doc("Asset Category", "Computers")
		row = next(row for row in asset_category.accounts if row.company_name == asset.company)
		row.fixed_asset_account = "Furniture and Fixtures - _TC"
		self.assertRaisesRegex(frappe.ValidationError, "Fixed Asset Account", asset_category.save)

		asset_category.reload()
		asset_category.accounts = [
			row for row in asset_category.accounts if row.company_name != asset.company
		]
		self.assertRaises(frappe.ValidationError, asset_category.save)

		asset.cancel()
		asset_category.reload()
		next(
			row for row in asset_category.accounts if row.company_name == asset.company
		).fixed_asset_account = "Furniture and Fixtures - _TC"
		asset_category.save()
