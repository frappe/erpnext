# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import json

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from erpnext.accounts.services.child_item_update import update_child_qty_rate
from erpnext.selling.doctype.sales_order.services.delivery_schedule import DeliveryScheduleService
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order


class TestDeliveryScheduleItem(IntegrationTestCase):
	def _scheduled_qty(self, so, sales_order_item):
		return frappe.get_all(
			"Delivery Schedule Item",
			filters={"sales_order": so.name, "sales_order_item": sales_order_item},
			pluck="qty",
		)

	def test_update_items_rescales_and_removes_schedules(self):
		so = make_sales_order(
			item_list=[
				{"item_code": "_Test Item", "qty": 10, "rate": 100, "warehouse": "_Test Warehouse - _TC"},
				{"item_code": "_Test Item 2", "qty": 6, "rate": 100, "warehouse": "_Test Warehouse - _TC"},
			],
			do_not_submit=True,
		)
		kept, removed = so.items[0], so.items[1]
		service = DeliveryScheduleService(so)
		service.create_delivery_schedule(
			kept, [{"delivery_date": today(), "qty": 5}, {"delivery_date": add_days(today(), 1), "qty": 5}]
		)
		service.create_delivery_schedule(
			removed, [{"delivery_date": today(), "qty": 3}, {"delivery_date": add_days(today(), 1), "qty": 3}]
		)
		so.submit()

		trans_items = [
			{
				"docname": kept.name,
				"item_code": kept.item_code,
				"qty": 4,
				"rate": kept.rate,
				"uom": kept.uom,
				"conversion_factor": kept.conversion_factor,
				"delivery_date": str(kept.delivery_date),
			},
		]
		update_child_qty_rate("Sales Order", json.dumps(trans_items), so.name)

		self.assertEqual(sorted(self._scheduled_qty(so, kept.name)), [4])
		self.assertEqual(self._scheduled_qty(so, removed.name), [])

	def test_draft_sales_order_with_schedule_can_be_deleted(self):
		so = make_sales_order(qty=10, do_not_submit=True)
		row = so.items[0]
		DeliveryScheduleService(so).create_delivery_schedule(
			row, [{"delivery_date": today(), "qty": row.qty}]
		)
		self.assertTrue(frappe.db.exists("Delivery Schedule Item", {"sales_order": so.name}))

		so.reload()
		so.delete()

		self.assertFalse(frappe.db.exists("Sales Order", so.name))
		self.assertFalse(frappe.db.exists("Delivery Schedule Item", {"sales_order": so.name}))

	def test_service_creates_schedules_on_system_managed_doctype(self):
		so = make_sales_order(qty=10, do_not_submit=True)
		row = so.items[0]
		DeliveryScheduleService(so).create_delivery_schedule(row, [{"delivery_date": today(), "qty": 10}])

		schedules = frappe.get_all(
			"Delivery Schedule Item",
			filters={"sales_order": so.name, "sales_order_item": row.name},
			fields=["qty", "stock_qty"],
		)
		self.assertEqual(len(schedules), 1)
		self.assertEqual(schedules[0].qty, 10)

	def test_schedule_of_another_order_is_not_taken_over(self):
		other_so = make_sales_order(qty=10, do_not_submit=True)
		DeliveryScheduleService(other_so).create_delivery_schedule(
			other_so.items[0], [{"delivery_date": today(), "qty": 10}]
		)
		other_schedule = frappe.get_all(
			"Delivery Schedule Item", {"sales_order": other_so.name}, pluck="name"
		)

		so = make_sales_order(qty=10, do_not_submit=True)
		row = so.items[0]
		DeliveryScheduleService(so).create_delivery_schedule(
			row, [{"name": other_schedule[0], "delivery_date": today(), "qty": 4}]
		)

		self.assertEqual(
			frappe.db.get_value("Delivery Schedule Item", other_schedule[0], ["sales_order", "qty"]),
			(other_so.name, 10),
		)
		self.assertEqual(self._scheduled_qty(so, row.name), [4])

		with self.assertRaises(frappe.ValidationError):
			DeliveryScheduleService(so).create_delivery_schedule(
				other_so.items[0], [{"delivery_date": today(), "qty": 1}]
			)

	def test_schedule_takes_item_details_from_the_order_row(self):
		so = make_sales_order(qty=10, do_not_submit=True)
		row = so.items[0]
		request_row = row.as_dict()
		request_row.update({"item_code": "_Test Item 2", "conversion_factor": 5, "warehouse": None})

		DeliveryScheduleService(so).create_delivery_schedule(
			request_row, [{"delivery_date": today(), "qty": 4}]
		)

		schedule = frappe.get_all(
			"Delivery Schedule Item",
			{"sales_order": so.name},
			["item_code", "warehouse", "conversion_factor", "stock_qty"],
		)
		self.assertEqual(len(schedule), 1)
		self.assertEqual(schedule[0].item_code, row.item_code)
		self.assertEqual(schedule[0].warehouse, row.warehouse)
		self.assertEqual(schedule[0].conversion_factor, row.conversion_factor)
		self.assertEqual(schedule[0].stock_qty, 4 * row.conversion_factor)

	def test_schedule_needs_write_access_to_the_order(self):
		so = make_sales_order(qty=10, do_not_submit=True)
		row = so.items[0]
		create_user("delivery-schedule-reader@example.com", "Stock User")

		frappe.set_user("delivery-schedule-reader@example.com")
		try:
			self.assertTrue(so.has_permission("read"))
			with self.assertRaises(frappe.PermissionError):
				so.create_delivery_schedule(row.as_dict(), [{"delivery_date": None, "qty": 10}])
		finally:
			frappe.set_user("Administrator")

		self.assertFalse(frappe.db.exists("Delivery Schedule Item", {"sales_order": so.name}))
