# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.assets.doctype.asset.depreciation import post_depreciation_entries, scrap_asset
from erpnext.assets.doctype.asset.test_asset import AssetSetup, create_asset
from erpnext.assets.report.fixed_asset_register.fixed_asset_register import execute


class TestFixedAssetRegister(AssetSetup):
	def run_report(self, **extra):
		filters = frappe._dict(company="_Test Company", **extra)
		return execute(filters)[1]

	def report_row(self, asset_name, **extra):
		return next(row for row in self.run_report(**extra) if row["asset_id"] == asset_name)

	def test_group_by_shows_only_permitted_assets(self):
		permitted_asset = create_asset(
			item_code="Macbook Pro", gross_purchase_amount=100000, purchase_amount=100000, submit=True
		)
		create_asset(item_code="Macbook Pro", gross_purchase_amount=50000, purchase_amount=50000, submit=True)

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

		self.assertEqual([row["gross_purchase_amount"] for row in rows], [100000])

	def test_disposed_assets_have_no_value(self):
		sold_asset = create_asset(item_code="Macbook Pro", gross_purchase_amount=100000, submit=True)
		create_sales_invoice(item_code="Macbook Pro", asset=sold_asset.name, qty=1, rate=80000)
		scrapped_asset = create_asset(item_code="Macbook Pro", gross_purchase_amount=100000, submit=True)
		scrap_asset(scrapped_asset.name)

		self.assertEqual(self.report_row(sold_asset.name)["asset_value"], 0)
		self.assertEqual(self.report_row(scrapped_asset.name)["asset_value"], 0)
		group_row = self.run_report(group_by="Asset Category", status="Disposed")[0]
		self.assertEqual(group_row["asset_value"], 0)
