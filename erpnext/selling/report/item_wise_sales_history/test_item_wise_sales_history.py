# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.selling.doctype.sales_order.mapper import make_sales_invoice
from erpnext.selling.doctype.sales_order.test_sales_order import (
	create_dn_against_so,
	make_sales_order,
)
from erpnext.selling.report.item_wise_sales_history.item_wise_sales_history import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestItemWiseSalesHistory(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"from_date": "2026-01-01",
				"to_date": "2026-12-31",
				**extra,
			}
		)
		return execute(filters)

	def so_row(self, so_name, **extra):
		data = self.run_report(**extra)[1]
		return next(row for row in data if row["sales_order"] == so_name)

	def test_sales_order_line_shown_with_values(self):
		so = make_sales_order(qty=10, rate=100, transaction_date="2026-06-01")

		row = self.so_row(so.name)
		self.assertEqual(row["item_code"], "_Test Item")
		self.assertEqual(row["quantity"], 10)
		self.assertEqual(row["rate"], 100)
		self.assertEqual(row["amount"], 1000)
		self.assertEqual(row["customer"], "_Test Customer")

	def test_draft_sales_order_excluded(self):
		so = make_sales_order(transaction_date="2026-06-01", do_not_submit=True)

		names = {row["sales_order"] for row in self.run_report()[1]}
		self.assertNotIn(so.name, names)

	def test_date_range_filters_on_transaction_date(self):
		so = make_sales_order(transaction_date="2026-06-01")

		in_range = {
			row["sales_order"] for row in self.run_report(from_date="2026-05-01", to_date="2026-07-01")[1]
		}
		self.assertIn(so.name, in_range)

		out_of_range = {
			row["sales_order"] for row in self.run_report(from_date="2026-01-01", to_date="2026-03-01")[1]
		}
		self.assertNotIn(so.name, out_of_range)

	def test_item_code_filter(self):
		so = make_sales_order(
			transaction_date="2026-06-01",
			item_list=[
				{"item_code": "_Test Item", "qty": 5, "rate": 100, "warehouse": "_Test Warehouse - _TC"},
				{"item_code": "_Test Item 2", "qty": 3, "rate": 200, "warehouse": "_Test Warehouse - _TC"},
			],
		)

		item_codes = {row["item_code"] for row in self.run_report(item_code="_Test Item 2")[1]}
		self.assertEqual(item_codes, {"_Test Item 2"})
		# the filtered-out line of the same order must not leak in
		self.assertTrue(
			all(row["sales_order"] == so.name for row in self.run_report(item_code="_Test Item 2")[1])
		)

	def test_customer_filter(self):
		make_sales_order(customer="_Test Customer 1", transaction_date="2026-06-01")
		make_sales_order(customer="_Test Customer 2", transaction_date="2026-06-01")

		customers = {row["customer"] for row in self.run_report(customer="_Test Customer 1")[1]}
		self.assertEqual(customers, {"_Test Customer 1"})

	def test_delivered_quantity_reflects_delivery(self):
		so = make_sales_order(qty=10, rate=100, transaction_date="2026-06-01")
		create_dn_against_so(so.name, delivered_qty=4)

		self.assertEqual(self.so_row(so.name)["delivered_quantity"], 4)

	def test_billed_amount_reflects_invoice(self):
		so = make_sales_order(qty=10, rate=100, transaction_date="2026-06-01")
		si = make_sales_invoice(so.name)
		si.insert()
		si.submit()

		self.assertEqual(self.so_row(so.name)["billed_amount"], 1000)

	def test_amounts_reported_in_company_currency(self):
		# a USD order must report rate/amount converted to the company's currency (base_* fields)
		so = make_sales_order(
			do_not_save=True,
			currency="USD",
			qty=10,
			rate=100,
			transaction_date="2026-06-01",
		)
		so.conversion_rate = 80
		so.insert()
		so.submit()

		row = self.so_row(so.name)
		self.assertEqual(row["rate"], 8000)  # 100 USD * 80
		self.assertEqual(row["amount"], 80000)  # 10 * 100 USD * 80

	def test_chart_aggregates_amount_per_item(self):
		make_sales_order(item_code="_Test Item", qty=2, rate=100, transaction_date="2026-06-01")
		make_sales_order(item_code="_Test Item", qty=3, rate=100, transaction_date="2026-06-01")

		chart = self.run_report(item_code="_Test Item")[3]
		labels = chart["data"]["labels"]
		values = chart["data"]["datasets"][0]["values"]
		self.assertIn("_Test Item", labels)
		# 2*100 + 3*100 aggregated for the item
		self.assertEqual(values[labels.index("_Test Item")], 500)
