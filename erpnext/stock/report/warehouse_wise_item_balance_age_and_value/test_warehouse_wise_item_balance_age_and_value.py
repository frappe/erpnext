# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
from erpnext.stock.report.warehouse_wise_item_balance_age_and_value.warehouse_wise_item_balance_age_and_value import (
	execute,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestWarehouseWiseItemBalanceAgeAndValue(ERPNextTestSuite):
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

	def test_balance_qty_and_value(self):
		item_code = "_Test Item"
		warehouse = "Stores - _TC"

		make_stock_entry(
			item_code=item_code,
			to_warehouse=warehouse,
			qty=10,
			rate=100,
			posting_date="2026-06-01",
		)
		make_stock_entry(
			item_code=item_code,
			from_warehouse=warehouse,
			qty=4,
			posting_date="2026-06-02",
		)

		data = self.run_report(item_code=item_code)

		# With a single (leaf) warehouse filter the row shape is:
		# [item, item_name, item_group, brand, value, age, bal_qty]
		rows = [row for row in data if row[0] == item_code]
		self.assertEqual(len(rows), 1)

		row = rows[0]
		# index 6 -> balance qty in the filtered warehouse
		self.assertEqual(row[6], 6)
		# index 4 -> total stock value (6 units @ 100)
		self.assertEqual(row[4], 600)

	def test_multiple_warehouse_filter(self):
		item_code = make_item(properties={"is_stock_item": 1}).name
		wh_a = create_warehouse("_Test Multi Balance WH A")
		wh_b = create_warehouse("_Test Multi Balance WH B")

		make_stock_entry(item_code=item_code, to_warehouse=wh_a, qty=10, rate=100, posting_date="2026-06-01")
		make_stock_entry(item_code=item_code, to_warehouse=wh_b, qty=25, rate=100, posting_date="2026-06-01")

		columns, data = self.run_report_with_columns(item_code=item_code, warehouse=[wh_a, wh_b])

		# a column per selected warehouse, preceded by the total qty column
		self.assertEqual(columns[-3:], ["Total Qty:Float:120", f"{wh_a}:Float:100", f"{wh_b}:Float:100"])

		rows = [row for row in data if row[0] == item_code]
		self.assertEqual(len(rows), 1)

		# [item, item_name, item_group, brand, value, age, total_qty, qty_wh_a, qty_wh_b]
		row = rows[0]
		self.assertEqual(row[4], 3500)
		self.assertEqual(row[-3:], [35, 10, 25])

	def test_group_warehouse_filter_expands_to_children(self):
		item_code = make_item(properties={"is_stock_item": 1}).name
		wh_a = create_warehouse("_Test Multi Balance WH A")

		make_stock_entry(item_code=item_code, to_warehouse=wh_a, qty=10, rate=100, posting_date="2026-06-01")

		columns, data = self.run_report_with_columns(
			item_code=item_code, warehouse=["_Test Warehouse Group - _TC"]
		)

		self.assertIn(f"{wh_a}:Float:100", columns)

		rows = [row for row in data if row[0] == item_code]
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0][columns.index(f"{wh_a}:Float:100")], 10)

	def test_multiple_item_filter(self):
		item_a = make_item(properties={"is_stock_item": 1}).name
		item_b = make_item(properties={"is_stock_item": 1}).name
		item_c = make_item(properties={"is_stock_item": 1}).name
		warehouse = create_warehouse("_Test Multi Balance WH A")

		for item_code, qty in ((item_a, 10), (item_b, 25), (item_c, 7)):
			make_stock_entry(
				item_code=item_code, to_warehouse=warehouse, qty=qty, rate=100, posting_date="2026-06-01"
			)

		data = self.run_report(item_code=[item_a, item_b], warehouse=warehouse)

		balances = {row[0]: row[-1] for row in data}
		self.assertEqual(balances.get(item_a), 10)
		self.assertEqual(balances.get(item_b), 25)
		self.assertNotIn(item_c, balances)

	def test_only_permitted_warehouses_are_shown(self):
		from frappe.permissions import add_user_permission

		item_code = make_item(properties={"is_stock_item": 1}).name
		make_stock_entry(
			item_code=item_code, to_warehouse="Stores - _TC", qty=7, rate=100, posting_date="2026-06-01"
		)

		user = "warehouse-age-value-user@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{"doctype": "User", "email": user, "first_name": "Age Value", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.get_doc("User", user).add_roles("Stock User")
		add_user_permission("Warehouse", "Finished Goods - _TC", user)

		frappe.set_user(user)
		try:
			columns, data = self.run_report_with_columns(item_code=[item_code])
		finally:
			frappe.set_user("Administrator")

		self.assertNotIn("Stores - _TC:Float:100", columns)
		self.assertEqual([row[4] for row in data if row[0] == item_code], [])

	def test_quantity_columns_keep_fractions(self):
		columns = self.run_report_with_columns(warehouse=["Stores - _TC", "Finished Goods - _TC"])[0]

		self.assertIn("Total Qty:Float:120", columns)
		self.assertIn("Stores - _TC:Float:100", columns)

	def test_group_warehouse_gets_no_column_of_its_own(self):
		columns = self.run_report_with_columns(warehouse=["_Test Warehouse Group - _TC"])[0]

		self.assertNotIn("_Test Warehouse Group - _TC:Float:100", columns)

	def test_negative_balances_are_not_filtered_as_zero(self):
		item_code = make_item(properties={"is_stock_item": 1, "allow_negative_stock": 1}).name
		make_stock_entry(
			item_code=item_code, from_warehouse="Stores - _TC", qty=3, rate=50, posting_date="2026-06-01"
		)

		data = self.run_report(item_code=item_code, filter_total_zero_qty=1)

		self.assertEqual([row[6] for row in data if row[0] == item_code], [-3])
