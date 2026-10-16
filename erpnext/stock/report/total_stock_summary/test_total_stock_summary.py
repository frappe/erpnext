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

	def test_warehouse_wise_quantity(self):
		item = "_Test Item"
		warehouse = "Stores - _TC"  # clean zero baseline for _Test Item
		make_stock_entry(item_code=item, to_warehouse=warehouse, qty=10, rate=100)

		# rows are (warehouse, item_code, description, actual_qty)
		row = next(r for r in self.run_report() if r[0] == warehouse and r[1] == item)
		self.assertEqual(row[3], 10)

	def test_only_non_zero_bins_are_listed(self):
		item = "_Test Item 2"
		warehouse = "Stores - _TC"  # clean zero baseline for _Test Item 2
		# receive then issue everything -> bin actual_qty back to zero
		make_stock_entry(item_code=item, to_warehouse=warehouse, qty=5, rate=100)
		make_stock_entry(item_code=item, from_warehouse=warehouse, qty=5)

		self.assertFalse([r for r in self.run_report() if r[0] == warehouse and r[1] == item])

	def test_company_totals_count_only_permitted_warehouses(self):
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
		add_user_permission("Warehouse", "Finished Goods - _TC", user)

		frappe.set_user(user)
		try:
			rows = self.run_report(group_by="Company")
		finally:
			frappe.set_user("Administrator")

		self.assertEqual([row[3] for row in rows if row[1] == item], [7])
