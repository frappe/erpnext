# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from types import SimpleNamespace
from unittest.mock import Mock, patch

import frappe
from frappe.tests import UnitTestCase

from erpnext.manufacturing.doctype.sales_forecast.sales_forecast import SalesForecast


class TestSalesForecast(UnitTestCase):
	def test_generate_demand_with_casefold_collision(self):
		forecast = SimpleNamespace(
			selected_items=[SimpleNamespace(item_code="SF-ss"), SimpleNamespace(item_code="SF-ẞ")],
			from_date="2026-01-01",
			frequency="Monthly",
			demand_number=1,
			items=[],
		)
		forecast.append = lambda field, demand: forecast.items.append(demand)

		items = [
			frappe._dict(name="SF-SS", item_name="ASCII Item", uom="Nos"),
			frappe._dict(name="SF-ẞ", item_name="Unicode Item", uom="Kg"),
		]
		db = SimpleNamespace(db_type="mariadb", get_value=Mock(side_effect=AssertionError))
		with patch.object(frappe, "get_all", return_value=items), patch.object(frappe, "db", db):
			SalesForecast.generate_manual_demand(forecast)

		self.assertEqual(
			[(row["item_name"], row["uom"]) for row in forecast.items],
			[("ASCII Item", "Nos"), ("Unicode Item", "Kg")],
		)

	def test_generated_dates_start_on_from_date(self):
		for frequency, expected in (
			("Monthly", ["2026-10-01", "2026-11-01", "2026-12-01"]),
			("Weekly", ["2026-10-01", "2026-10-08", "2026-10-15"]),
		):
			forecast = SimpleNamespace(
				selected_items=[SimpleNamespace(item_code="SF-DATES")],
				from_date="2026-10-01",
				frequency=frequency,
				demand_number=3,
				items=[],
			)
			forecast.append = lambda field, demand, forecast=forecast: forecast.items.append(demand)

			items = [frappe._dict(name="SF-DATES", item_name="Dates Item", uom="Nos")]
			db = SimpleNamespace(db_type="mariadb", get_value=Mock(side_effect=AssertionError))
			with patch.object(frappe, "get_all", return_value=items), patch.object(frappe, "db", db):
				SalesForecast.generate_manual_demand(forecast)

			self.assertEqual([str(row["delivery_date"]) for row in forecast.items], expected)
