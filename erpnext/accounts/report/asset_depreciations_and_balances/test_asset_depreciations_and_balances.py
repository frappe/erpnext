# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, today

from erpnext.accounts.report.asset_depreciations_and_balances.asset_depreciations_and_balances import (
	execute,
)
from erpnext.assets.doctype.asset.depreciation import scrap_asset
from erpnext.assets.doctype.asset.test_asset import AssetSetup, create_asset


class TestAssetDepreciationsAndBalancesReport(AssetSetup):
	def test_asset_scrapped_on_to_date_is_subtracted_once(self):
		asset = create_asset(submit=1)
		scrap_asset(asset.name)

		row = get_asset_row(asset.name, add_days(today(), -30), today())

		self.assertEqual(row.value_of_scrapped_asset, 100000)
		self.assertEqual(row.value_as_on_to_date, 0)
		self.assertEqual(row.net_asset_value_as_on_to_date, 0)


def get_asset_row(asset: str, from_date: str, to_date: str, **filters) -> frappe._dict:
	filters = frappe._dict(
		company="_Test Company",
		from_date=from_date,
		to_date=to_date,
		group_by="Asset",
		asset=asset,
		**filters,
	)
	return execute(filters)[1][0]
