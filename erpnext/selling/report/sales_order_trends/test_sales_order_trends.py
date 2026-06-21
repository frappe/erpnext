# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from erpnext.tests.utils import ERPNextTestSuite


class TestSalesOrderTrends(ERPNextTestSuite):
	def test_report_executes_with_group_by(self):
		# trends.get_data builds per-period SUM(CASE ...) aggregates (converted from MySQL SUM(IF)),
		# with a GROUP BY widened to every selected non-aggregated column and a based_on_key for the
		# group-by detail subqueries. Setting group_by exercises that full path on both engines.
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
