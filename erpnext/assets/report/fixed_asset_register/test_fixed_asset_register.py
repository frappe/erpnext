# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.assets.doctype.asset.test_asset import AssetSetup, create_asset
from erpnext.assets.report.fixed_asset_register.fixed_asset_register import execute


class TestFixedAssetRegister(AssetSetup):
	def test_report_lists_submitted_asset(self):
		"""Exercises the report's converted queries -- including the depreciation aggregate that groups
		by asset.name (must be valid on Postgres) -- by asserting a submitted asset is listed."""
		asset = create_asset(
			item_code="Macbook Pro",
			purchase_date="2020-01-01",
			available_for_use_date="2020-06-06",
			location="Test Location",
			submit=1,
		)
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"status": "In Location",
				"filter_based_on": "Date Range",
				"from_date": "2020-01-01",
				"to_date": "2030-12-31",
				"date_based_on": "Purchase Date",
			}
		)
		data = execute(filters)[1]
		asset_ids = {row.get("asset_id") for row in data}
		self.assertIn(asset.name, asset_ids)
