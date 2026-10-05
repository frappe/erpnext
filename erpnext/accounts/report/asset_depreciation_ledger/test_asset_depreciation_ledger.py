# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

from erpnext.accounts.report.asset_depreciation_ledger.asset_depreciation_ledger import execute
from erpnext.assets.doctype.asset.depreciation import post_depreciation_entries
from erpnext.assets.doctype.asset.test_asset import create_asset, set_depreciation_settings_in_company
from erpnext.tests.utils import ERPNextTestSuite


class TestAssetDepreciationLedger(ERPNextTestSuite):
	def setUp(self):
		set_depreciation_settings_in_company()

	def test_report_executes(self):
		# Smoke-guards the raw-SQL -> query-builder port: the report query must compile and run on
		# both MariaDB and postgres.
		company = frappe.db.get_value("Company", {}, "name")
		columns, *_rest = execute(
			frappe._dict({"company": company, "from_date": "2020-01-01", "to_date": "2030-12-31"})
		)
		self.assertTrue(columns)

	def test_accumulated_depreciation_is_of_the_selected_finance_book(self):
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
		post_depreciation_entries(date="2022-01-01")

		for finance_book, accumulated_depreciation in (
			("Test Finance Book 1", 50000),
			("Test Finance Book 2", 100000),
		):
			rows = get_asset_rows(asset.name, "2021-01-01", "2021-12-31", finance_book=finance_book)
			self.assertEqual(rows[-1].accumulated_depreciation_amount, accumulated_depreciation)


def get_asset_rows(asset: str, from_date: str, to_date: str, **filters) -> list[frappe._dict]:
	filters = frappe._dict(company="_Test Company", from_date=from_date, to_date=to_date, **filters)
	return [row for row in execute(filters)[1] if row.asset == asset]
