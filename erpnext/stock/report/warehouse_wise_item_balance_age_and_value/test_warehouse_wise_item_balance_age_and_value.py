# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
from erpnext.stock.report.warehouse_wise_item_balance_age_and_value.warehouse_wise_item_balance_age_and_value import (
	execute,
)


class TestWarehouseWiseItemBalanceAgeAndValue(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def run_report(self, **extra):
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"from_date": "2026-01-01",
				"to_date": "2026-12-31",
				"warehouse": "Stores - _TC",
			}
		)
		filters.update(extra)
		return execute(filters)[1]

	def run_report_with_columns(self, **extra):
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"from_date": "2026-01-01",
				"to_date": "2026-12-31",
			}
		)
		filters.update(extra)
		return execute(filters)

	def get_rows_for_restricted_user(self, item_code, warehouse, other_warehouses=(), **permission):
		from frappe.permissions import add_user_permission

		user = "warehouse-age-value-user@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{"doctype": "User", "email": user, "first_name": "Age Value", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.get_doc("User", user).add_roles("Stock User")
		add_user_permission("Warehouse", warehouse, user, **permission)
		for other_warehouse in other_warehouses:
			add_user_permission("Warehouse", other_warehouse, user)

		frappe.set_user(user)
		try:
			return self.run_report_with_columns(item_code=item_code)
		finally:
			frappe.set_user("Administrator")

	def make_stock_in_stores(self):
		item_code = make_item(properties={"is_stock_item": 1}).name
		make_stock_entry(
			item_code=item_code, to_warehouse="Stores - _TC", qty=7, rate=100, posting_date="2026-06-01"
		)
		return item_code

	def test_only_permitted_warehouses_are_shown(self):
		item_code = self.make_stock_in_stores()

		columns, data = self.get_rows_for_restricted_user(item_code, "Finished Goods - _TC")

		self.assertNotIn("Stores - _TC:Float:100", columns)
		self.assertEqual([row[4] for row in data if row[0] == item_code], [])

	def test_hidden_descendants_of_a_permitted_group_are_not_shown(self):
		item_code = self.make_stock_in_stores()
		group = frappe.db.get_value("Warehouse", "Stores - _TC", "parent_warehouse")

		columns, data = self.get_rows_for_restricted_user(item_code, group, hide_descendants=1)

		self.assertNotIn("Stores - _TC:Float:100", columns)
		self.assertEqual([row[4] for row in data if row[0] == item_code], [])

	def test_permission_for_another_doctype_does_not_limit_warehouses(self):
		item_code = self.make_stock_in_stores()

		columns, data = self.get_rows_for_restricted_user(
			item_code, "Finished Goods - _TC", applicable_for="Purchase Order"
		)

		self.assertEqual([row[4] for row in data if row[0] == item_code], [700])

	def test_permitted_warehouses_of_another_company_get_no_column(self):
		item_code = self.make_stock_in_stores()

		columns, data = self.get_rows_for_restricted_user(
			item_code, "Stores - _TC", other_warehouses=["_Test Warehouse 2 - _TC1"]
		)
		column_names = [column.split(":")[0] for column in columns]

		self.assertNotIn("_Test Warehouse 2 - _TC1", column_names)
		self.assertIn("Stores - _TC", column_names)
		self.assertEqual([row[4] for row in data if row[0] == item_code], [700])

	def test_quantity_columns_keep_fractions(self):
		columns = self.run_report_with_columns(warehouse=["Stores - _TC", "Finished Goods - _TC"])[0]

		self.assertIn("Total Qty:Float:120", columns)
		self.assertIn("Stores - _TC:Float:100", columns)

	def test_group_warehouse_gets_no_column_of_its_own(self):
		columns = self.run_report_with_columns(warehouse="_Test Warehouse Group - _TC")[0]

		self.assertNotIn("_Test Warehouse Group - _TC", [column.split(":")[0] for column in columns])

	def test_negative_balances_are_not_filtered_as_zero(self):
		item_code = make_item(properties={"is_stock_item": 1, "allow_negative_stock": 1}).name
		make_stock_entry(
			item_code=item_code, from_warehouse="Stores - _TC", qty=3, rate=50, posting_date="2026-06-01"
		)

		data = self.run_report(item_code=item_code, filter_total_zero_qty=1)

		self.assertEqual([row[6] for row in data if row[0] == item_code], [-3])
