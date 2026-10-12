# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.manufacturing.doctype.operation.test_operation import make_operation
from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.doctype.workstation.test_workstation import make_workstation
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.tests.utils import ERPNextTestSuite


class TestWorkstationType(ERPNextTestSuite):
	def test_disabled_workstation_not_picked_for_type_only_operation(self):
		workstation_type = create_workstation_type(workstation_type="_Test WT Disabled Pick").name
		disabled = make_workstation(
			workstation_name="_Test WS Disabled Pick Old", workstation_type=workstation_type
		)
		disabled.db_set("disabled", 1)
		active = make_workstation(
			workstation_name="_Test WS Disabled Pick New", workstation_type=workstation_type
		)

		fg_item = make_item("_Test FG Disabled Pick", {"is_stock_item": 1}).name
		rm_item = make_item("_Test RM Disabled Pick", {"is_stock_item": 1}).name
		operation = make_operation(operation="_Test Op Disabled Pick").name
		bom = make_bom(item=fg_item, raw_materials=[rm_item], with_operations=1, do_not_submit=True)
		bom.append(
			"operations",
			{
				"operation": operation,
				"workstation_type": workstation_type,
				"time_in_mins": 60,
				"hour_rate": 100,
			},
		)
		bom.submit()

		work_order = make_wo_order_test_record(item=fg_item, bom_no=bom.name, qty=1)
		workstation = frappe.db.get_value("Job Card", {"work_order": work_order.name}, "workstation")
		self.assertEqual(workstation, active.name)

	def test_type_cost_change_reaches_its_workstations(self):
		component = "_Test Component Type Rate"
		if not frappe.db.exists("Workstation Operating Component", component):
			frappe.get_doc(
				{"doctype": "Workstation Operating Component", "component_name": component}
			).insert()

		workstation_type = create_workstation_type(
			workstation_type="_Test WT Rate Change",
			workstation_costs=[{"operating_component": component, "operating_cost": 500}],
		)
		follows_type = make_workstation(
			workstation_name="_Test WS Rate Follows", workstation_type=workstation_type.name
		)
		own_rate = make_workstation(
			workstation_name="_Test WS Rate Own", workstation_type=workstation_type.name
		)
		own_rate.workstation_costs[0].operating_cost = 650
		own_rate.save()

		workstation_type.workstation_costs[0].operating_cost = 800
		workstation_type.save()

		self.assertEqual(frappe.db.get_value("Workstation", follows_type.name, "hour_rate"), 800)
		self.assertEqual(frappe.db.get_value("Workstation", own_rate.name, "hour_rate"), 650)


def create_workstation_type(**args):
	args = frappe._dict(args)

	if workstation_type := frappe.db.exists("Workstation Type", args.workstation_type):
		return frappe.get_doc("Workstation Type", workstation_type)
	else:
		doc = frappe.new_doc("Workstation Type")
		doc.update(args)
		doc.insert()
		return doc
