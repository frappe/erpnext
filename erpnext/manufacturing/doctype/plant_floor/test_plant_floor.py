# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.permissions import add_user_permission

from erpnext.manufacturing.doctype.plant_floor.plant_floor import get_stock_summary
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.page.shop_floor.shop_floor import get_work_orders
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.tests.utils import ERPNextTestSuite


class TestPlantFloor(ERPNextTestSuite):
	def test_shop_floor_work_orders_follow_user_permissions(self):
		allowed = make_wo_order_test_record(qty=1)
		restricted = make_wo_order_test_record(qty=1)
		user = create_user("shop-floor-restricted@example.com", "Manufacturing User")
		add_user_permission("Work Order", allowed.name, user.name)

		with self.set_user(user.name):
			hidden = get_work_orders("open", search=restricted.name)
			visible = get_work_orders("open", search=allowed.name)

		self.assertEqual(hidden["total"], 0)
		self.assertEqual(hidden["work_orders"], [])
		self.assertEqual([row.name for row in visible["work_orders"]], [allowed.name])

	def test_stock_summary_includes_child_item_groups(self):
		parent = make_item_group("_Test Plant Floor Parent Group", "All Item Groups", is_group=1)
		child = make_item_group("_Test Plant Floor Child Group", parent)
		item = make_item("_Test Plant Floor Item", {"is_stock_item": 1, "item_group": child}).name
		make_stock_entry(item_code=item, target="_Test Warehouse - _TC", qty=5, basic_rate=10)

		rows = get_stock_summary("_Test Warehouse - _TC", item_group=parent)
		self.assertIn(item, [row.item_code for row in rows])

	def test_group_or_other_company_warehouse_refused(self):
		for warehouse in ("All Warehouses - _TC", "Stores - TCP1"):
			plant_floor = frappe.get_doc(
				{
					"doctype": "Plant Floor",
					"floor_name": "_Test Plant Floor Bad Warehouse",
					"company": "_Test Company",
					"warehouse": warehouse,
				}
			)
			self.assertRaises(frappe.ValidationError, plant_floor.insert)


def make_item_group(name, parent, is_group=0):
	if not frappe.db.exists("Item Group", name):
		frappe.get_doc(
			{
				"doctype": "Item Group",
				"item_group_name": name,
				"parent_item_group": parent,
				"is_group": is_group,
			}
		).insert()
	return name
