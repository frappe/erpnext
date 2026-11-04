# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.permissions import add_user_permission

from erpnext.manufacturing.doctype.bom_creator.test_process_design import make_machine
from erpnext.manufacturing.doctype.work_order.services.plant_run.actions import PlantRun
from erpnext.manufacturing.doctype.work_order.test_plant_run import make_ketchup_work_order, minutes_ago
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.page.plant_builder.plant_builder import get_floor, get_floors, set_machine_floor
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

	def test_machines_join_and_leave_a_floor(self):
		work_order = make_ketchup_work_order()
		floor = make_floor()

		set_machine_floor("_Test Mixer", floor)
		data = get_floor(floor)
		self.assertEqual([machine.name for machine in data["machines"]], ["_Test Mixer"])
		self.assertEqual(data["machines"][0].machine_model, "Mixer")
		self.assertTrue(data["machines"][0].shapes)
		self.assertIn(work_order.name, [row.name for row in data["work_orders"]])
		floors = {row.name: row for row in get_floors()}
		self.assertEqual([machine.name for machine in floors[floor].machines], ["_Test Mixer"])

		set_machine_floor("_Test Mixer")
		self.assertEqual(get_floor(floor)["machines"], [])
		self.assertFalse(frappe.db.get_value("Workstation", "_Test Mixer", "plant_floor"))

	def test_floor_shows_the_job_running_on_each_machine(self):
		work_order = make_ketchup_work_order()
		floor = make_floor()
		set_machine_floor("_Test Mixer", floor)
		with minutes_ago(30):
			PlantRun(work_order.name).start()

		job = get_floor(floor)["machines"][0].job
		self.assertEqual((job.work_order, job.operation), (work_order.name, "_Test Mixer Operation"))

	def test_only_floor_writers_move_machines(self):
		make_machine("Mixer", "Mixer")
		floor = make_floor()
		reader = create_user("plant-floor-machine-reader@example.com", "Manufacturing User")
		with self.set_user(reader.name):
			self.assertRaises(frappe.PermissionError, set_machine_floor, "_Test Mixer", floor)

		self.assertRaisesRegex(
			frappe.ValidationError, "Choose the Plant Floor", set_machine_floor, "_Test Mixer"
		)

	def test_floor_is_read_only_without_plant_floor_write(self):
		floor = make_floor()
		reader = create_user("plant-builder-reader@example.com", "Manufacturing User")
		with self.set_user(reader.name):
			self.assertFalse(get_floor(floor)["can_write"])

		writer = create_user("plant-builder-writer@example.com", "Manufacturing Manager")
		writer.add_roles("Manufacturing User")
		with self.set_user(writer.name):
			self.assertTrue(get_floor(floor)["can_write"])


def make_floor():
	if not frappe.db.exists("Plant Floor", "_Test Ketchup Floor"):
		frappe.get_doc(
			{
				"doctype": "Plant Floor",
				"floor_name": "_Test Ketchup Floor",
				"company": "_Test Company",
				"warehouse": "Stores - _TC",
			}
		).insert()
	return "_Test Ketchup Floor"
