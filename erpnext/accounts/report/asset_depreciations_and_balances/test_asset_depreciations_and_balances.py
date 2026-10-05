# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, today

from erpnext.accounts.report.asset_depreciations_and_balances.asset_depreciations_and_balances import (
	execute,
)
from erpnext.assets.doctype.asset.depreciation import scrap_asset
from erpnext.assets.doctype.asset.test_asset import create_asset, set_depreciation_settings_in_company
from erpnext.tests.utils import ERPNextTestSuite


class TestAssetDepreciationsAndBalancesReport(ERPNextTestSuite):
	def setUp(self):
		set_depreciation_settings_in_company()

	def test_report_runs_on_both_engines(self):
		"""The report compared IfNull(asset.disposal_date, 0) against 0 -- coalescing a DATE
		column with integer 0. Postgres rejects that (COALESCE types date and integer cannot be
		matched) at plan time, so the whole report errored there regardless of data. It must run
		on both engines."""
		for group_by in ("Asset Category", "Asset"):
			filters = frappe._dict(
				company="_Test Company",
				from_date="2020-01-01",
				to_date="2030-12-31",
				group_by=group_by,
			)
			result = execute(filters)
			self.assertIsInstance(result[1], list)

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
