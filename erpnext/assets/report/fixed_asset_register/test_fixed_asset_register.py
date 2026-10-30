# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.assets.doctype.asset.depreciation import (
	post_depreciation_entries,
	restore_asset,
	scrap_asset,
)
from erpnext.assets.doctype.asset.test_asset import AssetSetup, create_asset
from erpnext.assets.report.fixed_asset_register.fixed_asset_register import execute


class TestFixedAssetRegister(AssetSetup):
	def run_report(self, **extra):
		filters = frappe._dict(company="_Test Company", **extra)
		return execute(filters)[1]

	def report_row(self, asset_name, **extra):
		return next(row for row in self.run_report(**extra) if row["asset_id"] == asset_name)

	def test_group_by_shows_only_permitted_assets(self):
		permitted_asset = create_asset(item_code="Macbook Pro", net_purchase_amount=100000, submit=True)
		create_asset(item_code="Macbook Pro", net_purchase_amount=50000, submit=True)

		user = "test_fixed_asset_register_permission@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": user,
					"first_name": "Asset Register",
					"roles": [{"role": "Accounts User"}],
				}
			).insert()
		frappe.permissions.add_user_permission("Asset", permitted_asset.name, user)

		frappe.set_user(user)
		try:
			rows = self.run_report(group_by="Asset Category")
		finally:
			frappe.set_user("Administrator")

		self.assertEqual([row["net_purchase_amount"] for row in rows], [100000])

	def test_disposed_assets_have_no_value(self):
		sold_asset = create_asset(item_code="Macbook Pro", net_purchase_amount=100000, submit=True)
		create_sales_invoice(item_code="Macbook Pro", asset=sold_asset.name, qty=1, rate=80000)
		scrapped_asset = create_asset(item_code="Macbook Pro", net_purchase_amount=100000, submit=True)
		scrap_asset(scrapped_asset.name)

		self.assertEqual(self.report_row(sold_asset.name)["asset_value"], 0)
		self.assertEqual(self.report_row(scrapped_asset.name)["asset_value"], 0)
		group_row = self.run_report(group_by="Asset Category", status="Disposed")[0]
		self.assertEqual(group_row["asset_value"], 0)

	def test_asset_with_only_named_finance_books_needs_its_book_selected(self):
		# the listing must not depend on whether other assets have a blank finance book
		frappe.db.delete("Asset Finance Book", {"finance_book": ("is", "not set")})
		asset = create_asset(item_code="Macbook Pro", available_for_use_date="2019-12-31", do_not_save=1)
		asset.calculate_depreciation = 1
		for finance_book in ("Test Finance Book 1", "Test Finance Book 2"):
			asset.append(
				"finance_books",
				{
					"finance_book": finance_book,
					"depreciation_method": "Straight Line",
					"frequency_of_depreciation": 12,
					"total_number_of_depreciations": 4,
					"depreciation_start_date": "2020-12-31",
				},
			)
		asset.submit()
		post_depreciation_entries(date="2021-01-01")

		self.assertNotIn(asset.name, {row["asset_id"] for row in self.run_report()})
		row = self.report_row(asset.name, finance_book="Test Finance Book 1")
		self.assertEqual(row["depreciated_amount"], 25000)

	def test_reversed_depreciation_is_not_counted(self):
		asset = create_asset(
			item_code="Macbook Pro",
			calculate_depreciation=1,
			available_for_use_date="2019-12-31",
			depreciation_start_date="2020-12-31",
			frequency_of_depreciation=12,
			total_number_of_depreciations=3,
			expected_value_after_useful_life=10000,
			submit=True,
		)
		post_depreciation_entries(date="2021-01-01")
		scrap_asset(asset.name, "2021-06-30")
		restore_asset(asset.name)

		row = self.report_row(asset.name)
		self.assertEqual(row["depreciated_amount"], 30000)
		self.assertEqual(row["asset_value"], 70000)

	def test_asset_disposed_after_period_keeps_its_value(self):
		period = dict(
			filter_based_on="Date Range",
			from_date="2015-01-01",
			to_date="2020-12-31",
			date_based_on="Purchase Date",
		)
		asset = create_asset(item_code="Macbook Pro", net_purchase_amount=100000, submit=True)
		group_value = self.run_report(group_by="Asset Category", **period)[0]["asset_value"]
		scrap_asset(asset.name, "2021-06-30")

		self.assertEqual(self.report_row(asset.name, **period)["asset_value"], 100000)
		self.assertEqual(self.run_report(group_by="Asset Category", **period)[0]["asset_value"], group_value)
		self.assertEqual(self.report_row(asset.name, **dict(period, to_date="2021-12-31"))["asset_value"], 0)
