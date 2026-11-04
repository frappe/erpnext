# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.stock.report.item_price_stock.item_price_stock import execute


class TestItemPriceStock(FrappeTestCase):
	def run_report(self, **extra):
		return execute(frappe._dict(extra))[1]

	def test_users_who_cannot_read_item_prices_cannot_run_it(self):
		user = "item-price-stock-sales-user@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{"doctype": "User", "email": user, "first_name": "Price Reader", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.get_doc("User", user).add_roles("Sales User", "Stock User")

		frappe.set_user(user)
		try:
			self.assertRaises(frappe.PermissionError, self.run_report, item_code="_Test Item")
		finally:
			frappe.set_user("Administrator")
