# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

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
