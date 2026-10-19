# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.total_stock_summary.total_stock_summary import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestTotalStockSummary(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = frappe._dict({"company": "_Test Company", "group_by": "Warehouse", **extra})
		return execute(filters)[1]

	def get_company_total_for_restricted_user(self, applicable_for=None):
		from frappe.permissions import add_user_permission

		from erpnext.stock.doctype.item.test_item import make_item

		item = make_item(properties={"is_stock_item": 1}).name
		for warehouse, qty in (("Stores - _TC", 40), ("Finished Goods - _TC", 7)):
			make_stock_entry(item_code=item, to_warehouse=warehouse, qty=qty, rate=100)

		user = "total-stock-summary-warehouse@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{"doctype": "User", "email": user, "first_name": "Stock Summary", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.get_doc("User", user).add_roles("Stock User")
		add_user_permission("Warehouse", "Finished Goods - _TC", user, applicable_for=applicable_for)

		frappe.set_user(user)
		try:
			rows = self.run_report(group_by="Company")
		finally:
			frappe.set_user("Administrator")

		return [row[3] for row in rows if row[1] == item]

	def test_company_totals_count_only_permitted_warehouses(self):
		self.assertEqual(self.get_company_total_for_restricted_user(), [7])

	def test_permission_for_another_doctype_does_not_limit_company_totals(self):
		self.assertEqual(self.get_company_total_for_restricted_user(applicable_for="Purchase Order"), [47])
