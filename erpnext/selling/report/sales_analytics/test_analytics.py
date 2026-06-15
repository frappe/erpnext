# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.utils import flt

from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.selling.report.sales_analytics.sales_analytics import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestAnalytics(ERPNextTestSuite):
	def test_sales_analytics(self):
		create_sales_orders()

		self.compare_result_for_customer()
		self.compare_result_for_customer_group()
		self.compare_result_for_customer_based_on_quantity()

	def compare_result_for_customer(self):
		filters = {
			"doc_type": "Sales Order",
			"range": "Monthly",
			"to_date": "2018-03-31",
			"tree_type": "Customer",
			"company": "_Test Company 2",
			"from_date": "2017-04-01",
			"value_quantity": "Value",
		}

		report = execute(filters)

		expected_data = [
			{
				"entity": "_Test Customer 1",
				"entity_name": "_Test Customer 1",
				"apr_2017": 0.0,
				"may_2017": 0.0,
				"jun_2017": 0.0,
				"jul_2017": 0.0,
				"aug_2017": 0.0,
				"oct_2017": 0.0,
				"sep_2017": 0.0,
				"nov_2017": 0.0,
				"dec_2017": 0.0,
				"jan_2018": 0.0,
				"feb_2018": 2000.0,
				"mar_2018": 0.0,
				"total": 2000.0,
			},
			{
				"entity": "_Test Customer 2",
				"entity_name": "_Test Customer 2",
				"apr_2017": 0.0,
				"may_2017": 0.0,
				"jun_2017": 0.0,
				"jul_2017": 0.0,
				"aug_2017": 0.0,
				"sep_2017": 1500.0,
				"oct_2017": 1000.0,
				"nov_2017": 0.0,
				"dec_2017": 0.0,
				"jan_2018": 0.0,
				"feb_2018": 0.0,
				"mar_2018": 0.0,
				"total": 2500.0,
			},
			{
				"entity": "_Test Customer 3",
				"entity_name": "_Test Customer 3",
				"apr_2017": 0.0,
				"may_2017": 0.0,
				"jun_2017": 2000.0,
				"jul_2017": 1000.0,
				"aug_2017": 0.0,
				"sep_2017": 0.0,
				"oct_2017": 0.0,
				"nov_2017": 0.0,
				"dec_2017": 0.0,
				"jan_2018": 0.0,
				"feb_2018": 0.0,
				"mar_2018": 0.0,
				"total": 3000.0,
			},
		]
		result = sorted(report[1], key=lambda k: k["entity"])
		self.assertEqual(expected_data, result)

	def compare_result_for_customer_group(self):
		filters = {
			"doc_type": "Sales Order",
			"range": "Monthly",
			"to_date": "2018-03-31",
			"tree_type": "Customer Group",
			"company": "_Test Company 2",
			"from_date": "2017-04-01",
			"value_quantity": "Value",
		}

		report = execute(filters)

		expected_first_row = {
			"entity": "All Customer Groups",
			"indent": 0,
			"apr_2017": 0.0,
			"may_2017": 0.0,
			"jun_2017": 2000.0,
			"jul_2017": 1000.0,
			"aug_2017": 0.0,
			"sep_2017": 1500.0,
			"oct_2017": 1000.0,
			"nov_2017": 0.0,
			"dec_2017": 0.0,
			"jan_2018": 0.0,
			"feb_2018": 2000.0,
			"mar_2018": 0.0,
			"total": 7500.0,
		}
		self.assertEqual(expected_first_row, report[1][0])

	def compare_result_for_customer_based_on_quantity(self):
		filters = {
			"doc_type": "Sales Order",
			"range": "Monthly",
			"to_date": "2018-03-31",
			"tree_type": "Customer",
			"company": "_Test Company 2",
			"from_date": "2017-04-01",
			"value_quantity": "Quantity",
		}

		report = execute(filters)

		expected_data = [
			{
				"entity": "_Test Customer 1",
				"entity_name": "_Test Customer 1",
				"apr_2017": 0.0,
				"may_2017": 0.0,
				"jun_2017": 0.0,
				"jul_2017": 0.0,
				"aug_2017": 0.0,
				"sep_2017": 0.0,
				"oct_2017": 0.0,
				"nov_2017": 0.0,
				"dec_2017": 0.0,
				"jan_2018": 0.0,
				"feb_2018": 20.0,
				"mar_2018": 0.0,
				"total": 20.0,
			},
			{
				"entity": "_Test Customer 2",
				"entity_name": "_Test Customer 2",
				"apr_2017": 0.0,
				"may_2017": 0.0,
				"jun_2017": 0.0,
				"jul_2017": 0.0,
				"aug_2017": 0.0,
				"sep_2017": 15.0,
				"oct_2017": 10.0,
				"nov_2017": 0.0,
				"dec_2017": 0.0,
				"jan_2018": 0.0,
				"feb_2018": 0.0,
				"mar_2018": 0.0,
				"total": 25.0,
			},
			{
				"entity": "_Test Customer 3",
				"entity_name": "_Test Customer 3",
				"apr_2017": 0.0,
				"may_2017": 0.0,
				"jun_2017": 20.0,
				"jul_2017": 10.0,
				"aug_2017": 0.0,
				"sep_2017": 0.0,
				"oct_2017": 0.0,
				"nov_2017": 0.0,
				"dec_2017": 0.0,
				"jan_2018": 0.0,
				"feb_2018": 0.0,
				"mar_2018": 0.0,
				"total": 30.0,
			},
		]
		result = sorted(report[1], key=lambda k: k["entity"])
		self.assertEqual(expected_data, result)


class TestSalesAnalyticsCoverage(ERPNextTestSuite):
	"""Covers the less-common branches of the Sales Analytics report.

	All tests reuse the FY2017-18 Sales Orders created by create_sales_orders()
	(grand total = 7500 in base currency / 75 stock qty across 3 customers).
	"""

	GRAND_TOTAL = 7500.0
	GRAND_QTY = 75.0

	def base_filters(self, **overrides):
		filters = {
			"doc_type": "Sales Order",
			"range": "Monthly",
			"to_date": "2018-03-31",
			"tree_type": "Customer",
			"company": "_Test Company 2",
			"from_date": "2017-04-01",
			"value_quantity": "Value",
		}
		filters.update(overrides)
		return filters

	def period_keys(self, report):
		# Period fieldnames are every "Float" column except the trailing "total".
		return [
			col["fieldname"]
			for col in report[0]
			if col.get("fieldtype") == "Float" and col["fieldname"] != "total"
		]

	def grand_total(self, report):
		return sum(flt(row.get("total", 0.0)) for row in report[1])

	# --- period ranges other than Monthly --------------------------------

	def test_quarterly_range(self):
		create_sales_orders()

		report = execute(self.base_filters(range="Quarterly", tree_type="Customer"))

		period_keys = self.period_keys(report)
		# FY2017-18 spans four calendar quarters; keys are scrubbed "Quarter N YYYY".
		self.assertTrue(all(key.startswith("quarter_") for key in period_keys))
		self.assertEqual(
			period_keys,
			["quarter_2_2017", "quarter_3_2017", "quarter_4_2017", "quarter_1_2018"],
		)

		result = sorted(report[1], key=lambda k: k["entity"])
		self.assertEqual(len(result), 3)

		# Customer 3: Jun (Q2) 2000 + Jul (Q3) 1000.
		c3 = next(r for r in result if r["entity"] == "_Test Customer 3")
		self.assertAlmostEqual(c3["quarter_2_2017"], 2000.0, places=2)
		self.assertAlmostEqual(c3["quarter_3_2017"], 1000.0, places=2)
		self.assertAlmostEqual(c3["total"], 3000.0, places=2)

		# Customer 2: Sep (Q3) 1500 + Oct (Q4) 1000.
		c2 = next(r for r in result if r["entity"] == "_Test Customer 2")
		self.assertAlmostEqual(c2["quarter_3_2017"], 1500.0, places=2)
		self.assertAlmostEqual(c2["quarter_4_2017"], 1000.0, places=2)
		self.assertAlmostEqual(c2["total"], 2500.0, places=2)

		# Customer 1: Feb 2018 (Q1 of next calendar year) 2000.
		c1 = next(r for r in result if r["entity"] == "_Test Customer 1")
		self.assertAlmostEqual(c1["quarter_1_2018"], 2000.0, places=2)
		self.assertAlmostEqual(c1["total"], 2000.0, places=2)

		# Totals still sum to the same grand total as Monthly.
		self.assertAlmostEqual(self.grand_total(report), self.GRAND_TOTAL, places=2)

	def test_yearly_range(self):
		create_sales_orders()

		monthly = execute(self.base_filters(range="Monthly", tree_type="Customer"))
		report = execute(self.base_filters(range="Yearly", tree_type="Customer"))

		# Yearly collapses the whole fiscal year into a single period column.
		self.assertEqual(len(self.period_keys(report)), 1)
		self.assertGreater(len(self.period_keys(monthly)), 1)

		period_key = self.period_keys(report)[0]
		result = sorted(report[1], key=lambda k: k["entity"])
		self.assertEqual(len(result), 3)

		# Each customer's single-period value equals its monthly total.
		expected = {
			"_Test Customer 1": 2000.0,
			"_Test Customer 2": 2500.0,
			"_Test Customer 3": 3000.0,
		}
		for row in result:
			self.assertAlmostEqual(row[period_key], expected[row["entity"]], places=2)
			self.assertAlmostEqual(row["total"], expected[row["entity"]], places=2)

		self.assertAlmostEqual(self.grand_total(report), self.GRAND_TOTAL, places=2)

	def test_weekly_range(self):
		create_sales_orders()

		report = execute(self.base_filters(range="Weekly", tree_type="Customer"))

		period_keys = self.period_keys(report)
		# Weekly buckets are scrubbed "Week N YYYY"; there should be many of them.
		self.assertTrue(all(key.startswith("week_") for key in period_keys))
		self.assertGreater(len(period_keys), 12)

		result = sorted(report[1], key=lambda k: k["entity"])
		self.assertEqual(len(result), 3)
		# Totals are range-independent.
		self.assertAlmostEqual(self.grand_total(report), self.GRAND_TOTAL, places=2)

	# --- tree types ------------------------------------------------------

	def test_order_type_tree(self):
		create_sales_orders()

		report = execute(self.base_filters(tree_type="Order Type"))

		# Order Type rolls grouped rows up under a synthetic "Order Types" parent.
		rows = report[1]
		parent = next(r for r in rows if r["entity"] == "Order Types")
		self.assertEqual(parent["indent"], 0)
		self.assertAlmostEqual(parent["total"], self.GRAND_TOTAL, places=2)

		# All fixture SOs default to order_type "Sales".
		sales = next(r for r in rows if r["entity"] == "Sales")
		self.assertEqual(sales["indent"], 1)
		self.assertAlmostEqual(sales["total"], self.GRAND_TOTAL, places=2)

		# Order Type column is rendered as free Data, not a Link.
		entity_col = report[0][0]
		self.assertEqual(entity_col["fieldtype"], "Data")
		self.assertEqual(entity_col["options"], "")

	def test_order_type_skipped_for_non_order_doctype(self):
		# Order Type only supports Quotation / Sales Order; otherwise data is empty.
		create_sales_orders()

		report = execute(self.base_filters(tree_type="Order Type", doc_type="Sales Invoice"))
		self.assertEqual(report[1], [])

	def test_item_group_tree(self):
		create_sales_orders()

		report = execute(self.base_filters(tree_type="Item Group"))

		# All fixture lines use _Test Item; resolve its group at runtime to stay robust.
		item_group = frappe.db.get_value("Item", "_Test Item", "item_group")

		rows = report[1]
		root = next(r for r in rows if r["entity"] == "All Item Groups")
		self.assertEqual(root["indent"], 0)
		self.assertAlmostEqual(root["total"], self.GRAND_TOTAL, places=2)

		leaf = next(r for r in rows if r["entity"] == item_group)
		self.assertAlmostEqual(leaf["total"], self.GRAND_TOTAL, places=2)

	def test_item_tree(self):
		create_sales_orders()

		report = execute(self.base_filters(tree_type="Item"))

		result = sorted(report[1], key=lambda k: k["entity"])
		self.assertEqual(len(result), 1)
		row = result[0]
		self.assertEqual(row["entity"], "_Test Item")
		# Item tree exposes a stock_uom column populated from the line items.
		self.assertIn("stock_uom", row)
		self.assertAlmostEqual(row["total"], self.GRAND_TOTAL, places=2)

	def test_item_quantity_value(self):
		# Item tree with Quantity uses stock_qty rather than base_net_amount.
		create_sales_orders()

		report = execute(self.base_filters(tree_type="Item", value_quantity="Quantity"))

		row = next(r for r in report[1] if r["entity"] == "_Test Item")
		self.assertAlmostEqual(row["total"], self.GRAND_QTY, places=2)

	def test_territory_tree(self):
		create_sales_orders()

		report = execute(self.base_filters(tree_type="Territory"))

		root = next(r for r in report[1] if r["entity"] == "All Territories")
		self.assertEqual(root["indent"], 0)
		# Whichever territories the fixture customers belong to, they roll up to the total.
		self.assertAlmostEqual(root["total"], self.GRAND_TOTAL, places=2)

	# --- parent-company subsidiary rollup --------------------------------

	def test_subsidiary_flag_on_non_group_company(self):
		# show_aggregate_value_from_subsidiary_companies is a no-op when the
		# selected company is not a group: the company list stays singular and
		# the totals match the plain Monthly run.
		create_sales_orders()

		base = execute(self.base_filters())
		report = execute(self.base_filters(show_aggregate_value_from_subsidiary_companies=1))

		self.assertAlmostEqual(self.grand_total(report), self.grand_total(base), places=2)
		self.assertAlmostEqual(self.grand_total(report), self.GRAND_TOTAL, places=2)

	# --- chart curve modes ----------------------------------------------

	def test_chart_total_curve(self):
		create_sales_orders()

		report = execute(self.base_filters(tree_type="Customer", curves="total"))
		chart = report[3]

		# "total" collapses every customer curve into a single "Total" dataset.
		self.assertEqual(len(chart["data"]["datasets"]), 1)
		dataset = chart["data"]["datasets"][0]
		self.assertEqual(dataset["name"], "Total")
		self.assertAlmostEqual(sum(dataset["values"]), self.GRAND_TOTAL, places=2)
		# Value reports render the chart as Currency.
		self.assertEqual(chart["fieldtype"], "Currency")

	def test_chart_total_curve_grouped(self):
		# For grouped (indented) trees, "total" keeps only the indent==0 rows.
		create_sales_orders()

		report = execute(self.base_filters(tree_type="Customer Group", curves="total"))
		chart = report[3]

		self.assertEqual(len(chart["data"]["datasets"]), 1)
		self.assertEqual(chart["data"]["datasets"][0]["name"], "All Customer Groups")
		self.assertAlmostEqual(sum(chart["data"]["datasets"][0]["values"]), self.GRAND_TOTAL, places=2)

	def test_chart_non_zeros_curve(self):
		create_sales_orders()

		report = execute(self.base_filters(tree_type="Customer", curves="non-zeros"))
		chart = report[3]

		# All three fixture customers have non-zero activity, so all are kept.
		names = sorted(d["name"] for d in chart["data"]["datasets"])
		self.assertEqual(names, ["_Test Customer 1", "_Test Customer 2", "_Test Customer 3"])
		for dataset in chart["data"]["datasets"]:
			self.assertGreater(sum(dataset["values"]), 0)

	def test_chart_quantity_fieldtype(self):
		# Quantity reports render the chart as Float, not Currency.
		create_sales_orders()

		report = execute(self.base_filters(tree_type="Customer", value_quantity="Quantity"))
		self.assertEqual(report[3]["fieldtype"], "Float")


def create_sales_orders():
	frappe.set_user("Administrator")

	make_sales_order(
		company="_Test Company 2",
		qty=10,
		customer="_Test Customer 1",
		transaction_date="2018-02-10",
		warehouse="Finished Goods - _TC2",
		currency="EUR",
	)

	make_sales_order(
		company="_Test Company 2",
		qty=10,
		customer="_Test Customer 1",
		transaction_date="2018-02-15",
		warehouse="Finished Goods - _TC2",
		currency="EUR",
	)

	make_sales_order(
		company="_Test Company 2",
		qty=10,
		customer="_Test Customer 2",
		transaction_date="2017-10-10",
		warehouse="Finished Goods - _TC2",
		currency="EUR",
	)

	make_sales_order(
		company="_Test Company 2",
		qty=15,
		customer="_Test Customer 2",
		transaction_date="2017-09-23",
		warehouse="Finished Goods - _TC2",
		currency="EUR",
	)

	make_sales_order(
		company="_Test Company 2",
		qty=20,
		customer="_Test Customer 3",
		transaction_date="2017-06-15",
		warehouse="Finished Goods - _TC2",
		currency="EUR",
	)

	make_sales_order(
		company="_Test Company 2",
		qty=10,
		customer="_Test Customer 3",
		transaction_date="2017-07-10",
		warehouse="Finished Goods - _TC2",
		currency="EUR",
	)
