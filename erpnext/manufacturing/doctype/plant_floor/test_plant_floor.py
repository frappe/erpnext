# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.permissions import add_user_permission

from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.page.shop_floor.shop_floor import get_work_orders
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
