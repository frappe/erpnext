# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.utils import add_days, nowdate

from erpnext.tests.utils import ERPNextTestSuite


class TestPurchaseOrderAnalysis(ERPNextTestSuite):
	def test_report_executes_and_lists_po(self):
		# get_data groups by (Purchase Order Item, Purchase Order) while selecting other parent
		# columns; this exercises that GROUP BY so the report stays valid on Postgres (which rejects
		# selecting non-grouped columns).
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
		from erpnext.buying.report.purchase_order_analysis.purchase_order_analysis import execute

		po = create_purchase_order(company="_Test Company")

		filters = {
			"company": "_Test Company",
			"from_date": add_days(nowdate(), -1),
			"to_date": add_days(nowdate(), 1),
		}
		result = execute(filters)
		columns, data = result[0], result[1]

		self.assertTrue(columns)
		self.assertIn(po.name, {row.get("purchase_order") for row in data})
