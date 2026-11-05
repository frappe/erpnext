# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt

from erpnext.manufacturing.report.exponential_smoothing_forecasting.exponential_smoothing_forecasting import (
	execute,
)
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.item.test_item import make_item

FROM_DATE = "2026-06-01"
TO_DATE = "2026-08-31"
SMOOTHING_CONSTANT = 0.5


class TestExponentialSmoothingForecasting(FrappeTestCase):
	def setUp(self):
		self.item = make_item(properties={"is_stock_item": 1}).name

	def tearDown(self):
		frappe.db.rollback()

	def test_future_forecast_stays_flat(self):
		self.create_sales_orders({"2026-03-15": 100, "2026-04-15": 100, "2026-05-15": 100})

		_columns, row = self.run_report(smoothing_constant=0.3)

		for month in ("jun_2026", "jul_2026", "aug_2026"):
			self.assertAlmostEqual(flt(row.get(f"forecast_{month}")), 100, places=6)

	def create_sales_orders(self, date_to_qty):
		for transaction_date, qty in date_to_qty.items():
			make_sales_order(item_code=self.item, qty=qty, transaction_date=transaction_date)

	def run_report(self, **extra):
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"based_on_document": "Sales Order",
				"based_on_field": "Qty",
				"no_of_years": 3,
				"periodicity": "Monthly",
				"from_date": FROM_DATE,
				"to_date": TO_DATE,
				"smoothing_constant": SMOOTHING_CONSTANT,
				"item_code": self.item,
			}
		)
		filters.update(extra)

		columns, data = execute(filters)[:2]
		item_row = next(
			(r for r in data if r.get("item_code") == self.item),
			None,
		)
		self.assertIsNotNone(item_row, f"{self.item} row missing from report output")
		return columns, item_row
