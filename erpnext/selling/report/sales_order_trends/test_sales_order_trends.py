# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import today

from erpnext.accounts.utils import get_fiscal_year
from erpnext.tests.utils import ERPNextTestSuite


class TestSalesOrderTrends(ERPNextTestSuite):
	def test_report_executes_with_group_by(self):
		# trends.get_data builds per-period SUM(CASE ...) aggregates (converted from MySQL SUM(IF)),
		# groups by the based-on KEY only (non-key descriptive columns like item_name/territory are
		# MAX()-aggregated so the report stays one row per key on both engines), and uses a based_on_key
		# for the group-by detail subqueries. Setting group_by exercises that full path on both engines.
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
		from erpnext.selling.report.sales_order_trends.sales_order_trends import execute

		make_sales_order(item_code="_Test Item", qty=3, rate=100)

		filters = {
			"company": "_Test Company",
			"period": "Monthly",
			"based_on": "Item",
			"group_by": "Customer",
		}
		columns, data, _chart_none, _chart = execute(filters)

		self.assertTrue(columns)
		self.assertTrue(any("_Test Item" in [str(cell) for cell in row] for row in data))

	def test_customer_with_divergent_stored_territory_stays_one_row(self):
		# territory (and customer_name) are stored per-transaction fields; historical sales docs can hold a
		# different value for the same customer. trends groups by t1.customer only and aggregates these with
		# Max(), so the report stays one row per customer on both MariaDB and Postgres. Grouping by territory
		# (the pre-fix behaviour) would split the customer into two rows.
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
		from erpnext.selling.report.sales_order_trends.sales_order_trends import execute

		make_sales_order(customer="_Test Customer", item_code="_Test Item", qty=3, rate=100)
		so2 = make_sales_order(customer="_Test Customer", item_code="_Test Item", qty=2, rate=100)
		# simulate a historical doc that stored a different territory for the same customer
		frappe.db.set_value("Sales Order", so2.name, "territory", "_Test Territory Rest Of The World")

		filters = {
			"company": "_Test Company",
			"period": "Monthly",
			"based_on": "Customer",
		}
		columns, data, _chart_none, _chart = execute(filters)

		self.assertTrue(columns)
		customer_rows = [row for row in data if row[0] == "_Test Customer"]
		self.assertEqual(len(customer_rows), 1)

	def test_total_row_not_double_counted_in_chart(self):
		# Regression test for the fix in trends.calculate_total_row that populates the
		# Total row's Currency column. Before the fix in get_chart_data (skipping the
		# Total row by label instead of `if not row[start]`), that populated Currency
		# cell made the Total-row-skip guard falsy, so the already-summed Total row got
		# added into the chart a second time (an SO of qty=3, rate=100 -> 300 read as 600).
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
		from erpnext.selling.report.sales_order_trends.sales_order_trends import execute

		make_sales_order(item_code="_Test Item", qty=3, rate=100, transaction_date=today())

		fiscal_year = get_fiscal_year(today())[0]
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"fiscal_year": fiscal_year,
				"period": "Monthly",
				"based_on": "Item",
			}
		)

		columns, data, _message, chart = execute(filters)
		self.assertTrue(columns)
		self.assertTrue(data)

		total_row = next(row for row in data if row[0] == f"'{_('Total')}'")
		expected_total = total_row[-1]  # Total(Amt) is the last column

		chart_total = sum(chart["data"]["datasets"][0]["values"])
		self.assertEqual(chart_total, expected_total)
		self.assertEqual(chart_total, 300)

	def test_chart_currency_matches_company_currency(self):
		# Regression test: the chart's "currency" key should reflect the transacting
		# company's currency (conditions["company_currency"]), not a stale global default.
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
		from erpnext.selling.report.sales_order_trends.sales_order_trends import execute

		make_sales_order(item_code="_Test Item", qty=1, rate=100, transaction_date=today())

		fiscal_year = get_fiscal_year(today())[0]
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"fiscal_year": fiscal_year,
				"period": "Monthly",
				"based_on": "Item",
			}
		)

		_columns, _data, _message, chart = execute(filters)
		expected_currency = frappe.get_cached_value("Company", "_Test Company", "default_currency")
		self.assertEqual(chart["currency"], expected_currency)

	def test_group_by_chart_matches_table_total_with_mixed_group_sizes(self):
		# _Test Item is split across two customers -> two detail rows under one header row.
		# _Test Item 2 has only one customer -> exactly one detail row under its header row.
		# A regression that double-counts header rows would inflate the chart above 600;
		# a regression that zeroes single-group rows would report less than 600.
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
		from erpnext.selling.report.sales_order_trends.sales_order_trends import execute

		make_sales_order(
			item_code="_Test Item", customer="_Test Customer", qty=3, rate=100, transaction_date=today()
		)
		make_sales_order(
			item_code="_Test Item", customer="_Test Customer 1", qty=2, rate=100, transaction_date=today()
		)
		make_sales_order(
			item_code="_Test Item 2", customer="_Test Customer", qty=1, rate=100, transaction_date=today()
		)

		fiscal_year = get_fiscal_year(today())[0]
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"fiscal_year": fiscal_year,
				"period": "Monthly",
				"based_on": "Item",
				"group_by": "Customer",
			}
		)

		columns, data, _message, chart = execute(filters)
		self.assertTrue(columns)
		self.assertTrue(data)

		total_row = next(row for row in data if row[0] == f"'{_('Total')}'")
		expected_total = total_row[-1]
		chart_total = sum(chart["data"]["datasets"][0]["values"])

		# 300 (item/customer) + 200 (item/customer1) + 100 (item2/customer) = 600
		self.assertEqual(expected_total, 600)
		self.assertEqual(chart_total, expected_total)

	def test_group_by_swapped_roles_based_on_customer_group_by_item(self):
		# Same regression, opposite role assignment: based_on="Customer" with group_by="Item".
		# Customer's based_on_cols (Customer, Customer Name, Territory, Currency) put the
		# group_by placeholder at a different column index than the Item-based_on case above,
		# exercising the alternate `inc`/`ind` arithmetic.
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
		from erpnext.selling.report.sales_order_trends.sales_order_trends import execute

		make_sales_order(
			item_code="_Test Item", customer="_Test Customer", qty=3, rate=100, transaction_date=today()
		)
		make_sales_order(
			item_code="_Test Item 2", customer="_Test Customer", qty=1, rate=100, transaction_date=today()
		)

		fiscal_year = get_fiscal_year(today())[0]
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"fiscal_year": fiscal_year,
				"period": "Monthly",
				"based_on": "Customer",
				"group_by": "Item",
			}
		)

		columns, data, _message, chart = execute(filters)
		total_row = next(row for row in data if row[0] == f"'{_('Total')}'")
		expected_total = total_row[-1]
		chart_total = sum(chart["data"]["datasets"][0]["values"])

		# 300 + 100 = 400
		self.assertEqual(expected_total, 400)
		self.assertEqual(chart_total, expected_total)

	def test_group_by_single_group_value_not_zeroed(self):
		# Isolates the specific failure mode flagged in review: a based_on value with exactly
		# one associated group value must still contribute its real amount to the chart, not 0.
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
		from erpnext.selling.report.sales_order_trends.sales_order_trends import execute

		make_sales_order(
			item_code="_Test Item", customer="_Test Customer", qty=2, rate=150, transaction_date=today()
		)

		fiscal_year = get_fiscal_year(today())[0]
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"fiscal_year": fiscal_year,
				"period": "Monthly",
				"based_on": "Item",
				"group_by": "Customer",
			}
		)

		columns, data, _message, chart = execute(filters)
		chart_total = sum(chart["data"]["datasets"][0]["values"])

		self.assertGreater(chart_total, 0)
		self.assertEqual(chart_total, 300)
