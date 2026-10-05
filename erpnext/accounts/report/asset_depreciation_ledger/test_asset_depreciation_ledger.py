# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import today

from erpnext.accounts.report.asset_depreciation_ledger.asset_depreciation_ledger import execute
from erpnext.assets.doctype.asset.depreciation import (
	post_depreciation_entries,
	restore_asset,
	scrap_asset,
)
from erpnext.assets.doctype.asset.test_asset import create_asset, set_depreciation_settings_in_company
from erpnext.assets.doctype.asset_value_adjustment.test_asset_value_adjustment import (
	make_asset_value_adjustment,
)
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

	def test_reversal_is_deducted_from_accumulated_depreciation(self):
		asset = create_depreciating_asset()
		post_depreciation_entries(date="2021-01-01")
		scrap_asset(asset.name, "2021-06-30")
		restore_asset(asset.name)

		rows = get_asset_rows(asset.name, "2020-01-01", today())
		depreciation_until_scrap = rows[1].depreciation_amount

		self.assertEqual(rows[-1].depreciation_amount, -depreciation_until_scrap)
		self.assertEqual(rows[-1].accumulated_depreciation_amount, 10000)
		self.assertEqual(rows[-1].value_after_depreciation, 90000)

	def test_value_after_depreciation_includes_revaluation(self):
		asset = create_depreciating_asset()
		post_depreciation_entries(date="2021-01-01")
		make_asset_value_adjustment(
			asset=asset.name, date="2021-01-15", current_asset_value=90000, new_asset_value=100000
		).submit()
		post_depreciation_entries(date="2022-01-01")

		rows = get_asset_rows(asset.name, "2020-01-01", "2021-12-31")

		self.assertEqual(rows[0].value_after_depreciation, 90000)
		self.assertAlmostEqual(
			rows[-1].value_after_depreciation, 110000 - rows[-1].accumulated_depreciation_amount, places=2
		)


def create_depreciating_asset(**args) -> frappe._dict:
	return create_asset(
		calculate_depreciation=1,
		available_for_use_date="2020-01-01",
		depreciation_start_date="2020-12-31",
		total_number_of_depreciations=10,
		submit=1,
		**args,
	)


def get_asset_rows(asset: str, from_date: str, to_date: str, **filters) -> list[frappe._dict]:
	filters = frappe._dict(company="_Test Company", from_date=from_date, to_date=to_date, **filters)
	return [row for row in execute(filters)[1] if row.asset == asset]
