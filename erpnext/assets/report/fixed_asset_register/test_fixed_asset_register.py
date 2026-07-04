# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.assets.doctype.asset.depreciation import post_depreciation_entries
from erpnext.assets.doctype.asset.test_asset import AssetSetup, create_asset
from erpnext.assets.doctype.asset_capitalization.test_asset_capitalization import (
	create_asset_capitalization,
)
from erpnext.assets.doctype.asset_value_adjustment.test_asset_value_adjustment import (
	make_asset_value_adjustment,
)
from erpnext.assets.report.fixed_asset_register.fixed_asset_register import execute


class TestFixedAssetRegister(AssetSetup):
	def run_report(self, **extra):
		filters = frappe._dict(company="_Test Company", **extra)
		return execute(filters)[1]

	def report_row(self, asset_name, **extra):
		return next(row for row in self.run_report(**extra) if row["asset_id"] == asset_name)

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
		ids = {
			row["asset_id"]
			for row in self.run_report(
				status="In Location",
				filter_based_on="Date Range",
				from_date="2020-01-01",
				to_date="2030-12-31",
				date_based_on="Purchase Date",
			)
		}
		self.assertIn(asset.name, ids)

	def test_asset_appears_with_purchase_value(self):
		asset = create_asset(
			item_code="Macbook Pro", net_purchase_amount=100000, purchase_amount=100000, submit=True
		)

		row = self.report_row(asset.name)
		self.assertEqual(row["net_purchase_amount"], 100000)
		self.assertEqual(row["asset_value"], 100000)  # no depreciation yet
		self.assertEqual(row["asset_category"], "Computers")

	def test_asset_value_reduced_by_opening_depreciation(self):
		asset = create_asset(
			item_code="Macbook Pro",
			net_purchase_amount=100000,
			purchase_amount=100000,
			opening_accumulated_depreciation=20000,
			opening_number_of_booked_depreciations=2,
			submit=True,
		)

		row = self.report_row(asset.name)
		self.assertEqual(row["opening_accumulated_depreciation"], 20000)
		self.assertEqual(row["asset_value"], 80000)  # 100000 - 20000

	def test_status_in_location_filter_shows_active_asset(self):
		asset = create_asset(
			item_code="Macbook Pro", net_purchase_amount=100000, purchase_amount=100000, submit=True
		)

		ids = {row["asset_id"] for row in self.run_report(status="In Location")}
		self.assertIn(asset.name, ids)

	def test_asset_category_filter(self):
		asset = create_asset(
			item_code="Macbook Pro", net_purchase_amount=100000, purchase_amount=100000, submit=True
		)

		ids = {row["asset_id"] for row in self.run_report(asset_category="Computers")}
		self.assertIn(asset.name, ids)

	def test_group_by_asset_category_sums_values(self):
		before_net, before_value = self.computers_group_totals()

		create_asset(item_code="Macbook Pro", net_purchase_amount=100000, purchase_amount=100000, submit=True)
		create_asset(
			item_code="Macbook Pro",
			asset_name="Macbook Pro 2",
			net_purchase_amount=50000,
			purchase_amount=50000,
			submit=True,
		)

		after_net, after_value = self.computers_group_totals()
		# assert on the delta so pre-existing Computers assets don't skew the totals
		self.assertEqual(after_net - before_net, 150000)
		self.assertEqual(after_value - before_value, 150000)

	def computers_group_totals(self):
		row = next(
			(r for r in self.run_report(group_by="Asset Category") if r["asset_category"] == "Computers"),
			None,
		)
		return (row["net_purchase_amount"], row["asset_value"]) if row else (0, 0)

	def test_booked_depreciation_reduces_asset_value(self):
		asset = create_asset(
			item_code="Macbook Pro",
			calculate_depreciation=1,
			available_for_use_date="2019-12-31",
			depreciation_start_date="2020-12-31",
			frequency_of_depreciation=12,
			total_number_of_depreciations=3,
			expected_value_after_useful_life=10000,
			net_purchase_amount=100000,
			purchase_amount=100000,
			submit=True,
		)

		# books one depreciation entry of (100000 - 10000) / 3 = 30000
		post_depreciation_entries(date="2021-01-01")

		row = self.report_row(asset.name)
		self.assertEqual(row["depreciated_amount"], 30000)
		self.assertEqual(row["asset_value"], 70000)  # 100000 - 30000

	def test_revaluation_adjusts_asset_value(self):
		asset = create_asset(
			item_code="Macbook Pro", net_purchase_amount=100000, purchase_amount=100000, submit=True
		)

		# revalue the asset upwards by 20000
		make_asset_value_adjustment(
			asset=asset.name, current_asset_value=100000, new_asset_value=120000
		).submit()

		row = self.report_row(asset.name)
		self.assertEqual(row["asset_value"], 120000)  # 100000 + 20000 revaluation

	def test_depreciation_and_revaluation_together(self):
		asset = create_asset(
			item_code="Macbook Pro",
			calculate_depreciation=1,
			available_for_use_date="2019-12-31",
			depreciation_start_date="2020-12-31",
			frequency_of_depreciation=12,
			total_number_of_depreciations=3,
			expected_value_after_useful_life=10000,
			net_purchase_amount=100000,
			purchase_amount=100000,
			submit=True,
		)

		# books one depreciation entry of (100000 - 10000) / 3 = 30000, leaving 70000
		post_depreciation_entries(date="2021-01-01")

		# revalue the depreciated asset down from 70000 to 60000
		make_asset_value_adjustment(
			asset=asset.name, current_asset_value=70000, new_asset_value=60000
		).submit()

		row = self.report_row(asset.name)
		self.assertEqual(row["depreciated_amount"], 30000)
		self.assertEqual(row["asset_value"], 60000)  # 100000 - 30000 depreciation - 10000 revaluation

	def test_sold_asset_hidden_from_in_location_and_shown_in_disposed(self):
		asset = create_asset(
			item_code="Macbook Pro", net_purchase_amount=100000, purchase_amount=100000, submit=True
		)

		create_sales_invoice(item_code="Macbook Pro", asset=asset.name, qty=1, rate=80000)
		self.assertEqual(frappe.db.get_value("Asset", asset.name, "status"), "Sold")

		self.assertNotIn(asset.name, {row["asset_id"] for row in self.run_report(status="In Location")})
		self.assertIn(asset.name, {row["asset_id"] for row in self.run_report(status="Disposed")})

	def test_capitalized_asset_hidden_from_in_location_and_shown_in_disposed(self):
		consumed_asset = create_asset(
			asset_name="Consumed Asset",
			net_purchase_amount=100000,
			purchase_amount=100000,
			submit=True,
		)
		composite_asset = create_asset(
			asset_name="Composite Asset", asset_type="Composite Asset", submit=False
		)

		create_asset_capitalization(
			target_asset=composite_asset.name, consumed_asset=consumed_asset.name, submit=1
		)
		self.assertEqual(frappe.db.get_value("Asset", consumed_asset.name, "status"), "Capitalized")

		self.assertNotIn(
			consumed_asset.name, {row["asset_id"] for row in self.run_report(status="In Location")}
		)
		self.assertIn(consumed_asset.name, {row["asset_id"] for row in self.run_report(status="Disposed")})
