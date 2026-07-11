# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import flt

from erpnext.manufacturing.report.exponential_smoothing_forecasting.exponential_smoothing_forecasting import (
	execute,
)
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.tests.utils import ERPNextTestSuite

FROM_DATE = "2026-06-01"
TO_DATE = "2026-08-31"
SMOOTHING_CONSTANT = 0.5


class TestExponentialSmoothingForecasting(ERPNextTestSuite):
	"""Drive real submitted Sales Orders and assert the report buckets the ordered
	quantities into the correct historical periods and produces a forecast."""

	def setUp(self):
		# The forecast query has no lower date bound, so it would pick up any committed
		# Sales Order for the item. A uniquely-named item keeps the buckets scoped to
		# just this test's orders.
		self.item = make_item(properties={"is_stock_item": 1}).name

	def test_monthly_qty_forecast_from_sales_orders(self):
		# Historical demand: distinct calendar months strictly before FROM_DATE.
		# Monthly period keys are derived from the period's last day (e.g. "mar_2026").
		history = {"mar_2026": 7, "apr_2026": 4, "may_2026": 9}
		self.create_sales_orders(
			{
				"2026-03-15": history["mar_2026"],
				"2026-04-15": history["apr_2026"],
				"2026-05-15": history["may_2026"],
			}
		)

		columns, row = self.run_report()
		fields = {col["fieldname"] for col in columns}

		# For Monthly periodicity only future periods are exposed as columns, each as a
		# forecast_ field. Historical demand lives in the row data (keyed by month) but is
		# not surfaced as its own column.
		self.assertIn("forecast_jun_2026", fields, "expected future forecast column")
		self.assertNotIn("jun_2026", fields, "future period must not expose raw demand column")
		self.assertNotIn("mar_2026", fields, "historical month is not a Monthly report column")

		# Historical buckets must exactly reflect the ordered quantities.
		for key, qty in history.items():
			self.assertEqual(flt(row.get(key)), flt(qty), f"bucket {key} mismatch")

		# The forecast seeds at the average of the non-zero historical months and then
		# smooths through them in order: F = F + a*(actual - F). Asserting the exact
		# analytical value pins the smoothing formula (Jun 2026 works out to ~7.2083).
		expected_avg = sum(history.values()) / len(history)
		self.assertAlmostEqual(flt(row.get("avg")), expected_avg, places=6)

		forecast = expected_avg
		for month in ("mar_2026", "apr_2026", "may_2026"):
			forecast = forecast + SMOOTHING_CONSTANT * (history[month] - forecast)
		self.assertAlmostEqual(flt(row.get("forecast_jun_2026")), forecast, places=6)

	def test_ignores_documents_outside_range_and_other_docstatus(self):
		self.create_sales_orders({"2026-05-10": 6})
		# A draft SO and a future-dated SO must not contribute to historical demand.
		make_sales_order(item_code=self.item, qty=100, transaction_date="2026-05-20", do_not_submit=True)
		make_sales_order(item_code=self.item, qty=100, transaction_date=FROM_DATE)

		_columns, row = self.run_report()
		self.assertEqual(flt(row.get("may_2026")), 6.0)

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
