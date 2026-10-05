# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, today

from erpnext.accounts.report.asset_depreciations_and_balances.asset_depreciations_and_balances import (
	execute,
)
from erpnext.assets.doctype.asset.depreciation import post_depreciation_entries, scrap_asset
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

	def test_depreciation_without_finance_book_filter_shows_only_the_default_book(self):
		asset = create_asset(available_for_use_date="2019-12-31", do_not_save=1)
		asset.calculate_depreciation = 1
		for finance_book, total_number_of_depreciations in (
			("Test Finance Book 1", 4),
			("Test Finance Book 2", 2),
		):
			asset.append(
				"finance_books",
				{
					"finance_book": finance_book,
					"depreciation_method": "Straight Line",
					"frequency_of_depreciation": 12,
					"total_number_of_depreciations": total_number_of_depreciations,
					"depreciation_start_date": "2020-12-31",
				},
			)
		asset.submit()
		post_depreciation_entries(date="2021-01-01")

		row = get_asset_row(asset.name, "2020-01-01", "2021-06-30")
		self.assertEqual(row.accumulated_depreciation_as_on_to_date, 0)

		frappe.db.set_value("Company", "_Test Company", "default_finance_book", "Test Finance Book 1")
		row = get_asset_row(asset.name, "2020-01-01", "2021-06-30")
		self.assertEqual(row.accumulated_depreciation_as_on_to_date, 25000)

		row = get_asset_row(asset.name, "2020-01-01", "2021-06-30", finance_book="Test Finance Book 2")
		self.assertEqual(row.accumulated_depreciation_as_on_to_date, 50000)


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
