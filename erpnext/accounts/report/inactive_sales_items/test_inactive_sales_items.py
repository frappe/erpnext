# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, today

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.inactive_sales_items.inactive_sales_items import execute
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.tests.utils import ERPNextTestSuite


class TestInactiveSalesItems(ERPNextTestSuite):
	def test_days_since_last_order_is_computed(self):
		# Exercises the date-arithmetic path (DATEDIFF/CURRENT_DATE on mariadb, date subtraction on
		# postgres) which must produce the same integer day count on both databases.
		item = make_item("_Test Inactive Sales Item").name
		old_date = add_days(today(), -120)
		so = make_sales_order(item=item, qty=3, rate=150, transaction_date=old_date)
		so.items[0].delivery_date = add_days(old_date, 7)
		so.save()
		so.submit()

		columns, data = execute(frappe._dict({"based_on": "Sales Order", "days": 30}))
		self.assertTrue(columns)
		row = next((r for r in data if r.get("item") == item and r.get("days_since_last_order")), None)
		self.assertIsNotNone(row, "Inactive item should appear in the report")
		self.assertGreaterEqual(row["days_since_last_order"], 30)

	def test_report_runs_for_sales_invoice(self):
		columns, _data = execute(frappe._dict({"based_on": "Sales Invoice", "days": 30}))
		self.assertTrue(columns)

	def test_group_territory_includes_sales_of_child_territories(self):
		item = make_item("_Test Inactive Sales Item Territory").name
		create_sales_invoice(item=item, qty=1, rate=100)

		data = self.run_report(territory="All Territories")

		self.assertNotIn(item, [row["item"] for row in data])

	def run_report(self, **filters) -> list[dict]:
		return execute(frappe._dict(based_on="Sales Invoice", days=30, **filters))[1]
