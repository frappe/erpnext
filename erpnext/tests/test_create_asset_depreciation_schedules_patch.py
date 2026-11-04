# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.assets.doctype.asset.test_asset import AssetSetup, create_asset
from erpnext.patches.v15_0.create_asset_depreciation_schedules_from_assets import (
	create_asset_depr_schedule,
	get_asset_finance_books_map,
)


class TestCreateAssetDepreciationSchedulesPatch(AssetSetup):
	def test_schedule_takes_value_after_depreciation_from_finance_book(self):
		asset = create_asset(
			item_code="Macbook Pro", calculate_depreciation=1, depreciation_start_date="2020-12-31"
		)
		# differs from net_purchase_amount - opening_accumulated_depreciation (100000)
		frappe.db.set_value(
			"Asset Finance Book", asset.finance_books[0].name, "value_after_depreciation", 70000
		)

		fb_row = get_asset_finance_books_map()[(asset.name, "")]
		schedule = create_asset_depr_schedule(fb_row)

		self.assertEqual(schedule.asset, asset.name)
		self.assertEqual(schedule.value_after_depreciation, 70000)
