# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.permissions import add_user_permission

from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.buying.report.item_wise_purchase_history.item_wise_purchase_history import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestItemWisePurchaseHistory(ERPNextTestSuite):
	def test_restricted_user_sees_only_permitted_suppliers_in_rows_and_chart(self):
		create_purchase_order(supplier="_Test Supplier", qty=10, rate=100, transaction_date="2026-06-01")
		create_purchase_order(supplier="_Test Supplier 1", qty=4, rate=250, transaction_date="2026-06-01")
		user = create_user("purchase_history_restricted@example.com", "Purchase User").name
		add_user_permission("Supplier", "_Test Supplier", user)

		filters = frappe._dict(company="_Test Company", from_date="2026-06-01", to_date="2026-06-01")
		with self.set_user(user):
			_columns, data, _message, chart = execute(filters)

		self.assertEqual({row["supplier"] for row in data}, {"_Test Supplier"})
		self.assertEqual(chart["data"]["datasets"][0]["values"], [1000])
