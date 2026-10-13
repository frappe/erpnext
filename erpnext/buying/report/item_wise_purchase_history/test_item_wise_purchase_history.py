# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.permissions import add_user_permission
from frappe.tests.utils import FrappeTestCase

from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.buying.report.item_wise_purchase_history.item_wise_purchase_history import execute


class TestItemWisePurchaseHistory(FrappeTestCase):
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

	def test_parent_item_group_filter_includes_child_groups(self):
		po = create_purchase_order(item_code="_Test Item", transaction_date="2026-06-01")

		names = {row["purchase_order"] for row in self.run_report(item_group="All Item Groups")[1]}
		self.assertIn(po.name, names)

	def test_runs_without_dates(self):
		po = create_purchase_order(transaction_date="2026-06-01")

		names = {row["purchase_order"] for row in execute({"company": "_Test Company"})[1]}
		self.assertIn(po.name, names)

	def test_restricted_user_sees_only_permitted_suppliers_in_rows_and_chart(self):
		create_purchase_order(supplier="_Test Supplier", qty=10, rate=100, transaction_date="2026-06-02")
		create_purchase_order(supplier="_Test Supplier 1", qty=4, rate=250, transaction_date="2026-06-02")
		user = create_user("purchase_history_restricted@example.com", "Purchase User").name
		add_user_permission("Supplier", "_Test Supplier", user)

		filters = frappe._dict(company="_Test Company", from_date="2026-06-02", to_date="2026-06-02")
		with self.set_user(user):
			_columns, data, _message, chart = execute(filters)

		self.assertEqual({row["supplier"] for row in data}, {"_Test Supplier"})
		self.assertEqual(chart["data"]["datasets"][0]["values"], [1000])
