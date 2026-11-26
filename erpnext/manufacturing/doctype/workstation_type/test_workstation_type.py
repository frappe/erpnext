# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.manufacturing.doctype.operation.test_operation import make_operation
from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.doctype.workstation.test_workstation import make_workstation
from erpnext.manufacturing.doctype.workstation_type.workstation_type import (
	DEFAULT_WORKSTATION_TYPES,
	create_default_workstation_types,
	get_preset_shapes,
	get_workstation_details,
)
from erpnext.manufacturing.page.plant_builder.plant_builder import (
	add_machine_shapes,
	get_machine_catalog,
	save_machine_design,
)
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

	@ERPNextTestSuite.change_settings("Manufacturing Settings", {"disable_capacity_planning": 0})
	def test_type_without_enabled_workstation_gives_a_clear_error(self):
		workstation_type = create_workstation_type(workstation_type="_Test WT All Disabled").name
		make_workstation(workstation_name="_Test WS All Disabled", workstation_type=workstation_type).db_set(
			"disabled", 1
		)

		fg_item = make_item("_Test FG All Disabled", {"is_stock_item": 1}).name
		rm_item = make_item("_Test RM All Disabled", {"is_stock_item": 1}).name
		operation = make_operation(operation="_Test Op All Disabled").name
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

		self.assertRaisesRegex(
			frappe.ValidationError,
			"has no enabled Workstation",
			make_wo_order_test_record,
			item=fg_item,
			bom_no=bom.name,
			qty=1,
		)

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

	def test_copy_preset_shapes_fills_the_table(self):
		workstation_type = create_workstation_type(
			workstation_type="_Test WT Reactor Shapes", machine_model="Reactor"
		)
		workstation_type.copy_preset_shapes()
		workstation_type.save()

		preset = get_preset_shapes("Reactor")
		self.assertEqual([row.shape for row in workstation_type.shapes], [row["shape"] for row in preset])
		self.assertEqual(workstation_type.shapes[1].finish, "Heat")
		self.assertEqual(workstation_type.shapes[0].radius, 50)

	def test_type_without_shapes_draws_its_preset(self):
		mixer = create_workstation_type(workstation_type="_Test WT Mixer Preset", machine_model="Mixer")
		plain = create_workstation_type(workstation_type="_Test WT Plain Preset")

		self.assertEqual(mixer.machine_shapes, get_preset_shapes("Mixer"))
		self.assertEqual(plain.machine_shapes, get_preset_shapes("Machine"))

	def test_shape_needs_a_size(self):
		workstation_type = create_workstation_type(workstation_type="_Test WT Flat Tank")
		workstation_type.append("shapes", {"shape": "Tank", "radius": 0, "height": 80})

		self.assertRaisesRegex(frappe.ValidationError, "Radius greater than zero", workstation_type.save)

	def test_catalog_offers_types_with_shapes_only(self):
		create_workstation_type(workstation_type="_Test WT No Design")
		save_machine_design(
			create_workstation_type(workstation_type="_Test WT Own Design").name,
			[{"shape": "Box", "finish": "Dark", "width": 50, "depth": 40, "height": 60}],
		)

		names = [row.name for row in get_machine_catalog()["workstation_types"]]
		self.assertIn("_Test WT Own Design", names)
		self.assertNotIn("_Test WT No Design", names)

	def test_plant_machine_carries_the_type_shapes(self):
		workstation_type = create_workstation_type(workstation_type="_Test WT Plant Shapes")
		save_machine_design(
			workstation_type.name,
			[{"shape": "Open Tank", "finish": "Product", "radius": 30, "height": 60, "shows_level": 1}],
		)
		workstation = make_workstation(
			workstation_name="_Test WS Plant Shapes", workstation_type=workstation_type.name
		)

		machines = add_machine_shapes(get_workstation_details((workstation.name,)))
		shapes = machines[workstation.name]["shapes"]
		self.assertEqual([(row["shape"], row["radius"]) for row in shapes], [("Open Tank", 30)])

	def test_default_workstation_types_are_added_once_and_keep_existing_ones(self):
		names = [row["workstation_type"] for row in frappe.get_file_json(DEFAULT_WORKSTATION_TYPES)]
		for name in names:
			frappe.delete_doc_if_exists("Workstation Type", name, force=True)
		create_workstation_type(workstation_type="Dryer", description="Our own dryer")

		create_default_workstation_types()
		create_default_workstation_types()

		self.assertEqual(frappe.db.count("Workstation Type", {"name": ("in", names)}), len(names))
		self.assertEqual(frappe.db.get_value("Workstation Type", "Dryer", "description"), "Our own dryer")
		self.assertEqual(len(frappe.get_doc("Workstation Type", "Ring Frame").shapes), 9)
		self.assertEqual(
			frappe.get_doc("Workstation Type", "Mixer").machine_shapes, get_preset_shapes("Mixer")
		)


def create_workstation_type(**args):
	args = frappe._dict(args)

	if workstation_type := frappe.db.exists("Workstation Type", args.workstation_type):
		return frappe.get_doc("Workstation Type", workstation_type)
	else:
		doc = frappe.new_doc("Workstation Type")
		doc.update(args)
		doc.insert()
		return doc
