# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.permissions import add_user_permission
from frappe.utils import add_to_date, now_datetime

from erpnext.manufacturing.doctype.plant_floor.plant_floor import get_stock_summary
from erpnext.manufacturing.doctype.work_order.services.plant_run.actions import PlantRun
from erpnext.manufacturing.doctype.work_order.services.plant_run.state import PlantRunState
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.page.shop_floor.shop_floor import get_work_orders
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
from erpnext.stock.utils import get_stock_balance
from erpnext.tests.utils import ERPNextTestSuite

STORE = "Stores - _TC"
FINISHED_GOODS = "Finished Goods - _TC"


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

	def test_batch_plan_scales_formula_by_stage_yields(self):
		plan = make_ketchup_plant().get_batch_plan(2000).as_dict()

		self.assertEqual(plan.output_weight, 1000)
		self.assertEqual(plan.input_weight, 1250)
		materials = {row.item_code: row for row in plan.materials}
		self.assertEqual(materials["_Test Tomato Paste"].qty, 500)
		self.assertEqual(materials["_Test Process Water"].percentage, 30)
		self.assertEqual(materials["_Test Process Water"].qty, 375)
		self.assertEqual([row.output_qty for row in plan.stages], [1250, 1000, 2000])
		self.assertEqual([row.is_packing for row in plan.stages], [False, False, True])
		self.assertEqual(plan.packing_materials[0].qty, 2000)

	def test_setup_errors_list_what_is_missing(self):
		plant_floor = make_ketchup_plant()
		self.assertEqual(plant_floor.setup_errors, [])

		plant_floor.materials[1].is_balance_item = 0
		plant_floor.materials[1].percentage = 20
		plant_floor.stages.pop()
		errors = plant_floor.setup_errors

		self.assertIn("The formula adds up to 90.0%. Make it 100% or pick a balance item.", errors)
		self.assertIn("End with exactly one packing stage, a Filling Line or a Bagging Line", errors)

	def test_work_order_without_bom_from_plant_floor(self):
		plant_floor = make_ketchup_plant()
		work_order = plant_floor.make_work_order(2000)

		self.assertFalse(work_order.bom_no)
		self.assertTrue(work_order.track_semi_finished_goods)
		self.assertEqual(
			[(row.finished_good, row.output_qty) for row in work_order.operations],
			[
				("_Test Ketchup Pre-mix", 1250),
				("_Test Cooked Ketchup Base", 1000),
				("_Test Ketchup Bottle", 0),
			],
		)
		self.assertEqual(work_order.operations[1].wip_warehouse, "_Test Kettle Warehouse - _TC")
		required = {(row.operation_row_id, row.item_code): row for row in work_order.required_items}
		self.assertEqual(required[(1, "_Test Tomato Paste")].required_qty, 500)
		self.assertEqual(
			required[(2, "_Test Ketchup Pre-mix")].source_warehouse, "_Test Mixer Warehouse - _TC"
		)
		self.assertEqual(required[(3, "_Test Ketchup PET Bottle")].source_warehouse, STORE)

		work_order.qty = 1000
		work_order.save()
		required = {(row.operation_row_id, row.item_code): row for row in work_order.required_items}
		self.assertEqual(required[(1, "_Test Tomato Paste")].required_qty, 250)
		self.assertEqual(work_order.operations[1].output_qty, 500)

	def test_work_order_needs_bom_or_plant_floor(self):
		work_order = frappe.new_doc("Work Order")
		work_order.update({"production_item": make_ketchup_items(), "company": "_Test Company", "qty": 1})
		self.assertRaises(frappe.MandatoryError, work_order.insert)

	def test_plant_floor_run_moves_stock_through_machines(self):
		plant_floor = make_ketchup_plant()
		stock_ketchup_materials()
		work_order = plant_floor.make_work_order(2000)

		run_stage(
			work_order,
			180,
			150,
			output_qty=1250,
			actual={"_Test Tomato Paste": 505},
		)
		self.assertEqual(get_stock_balance("_Test Tomato Paste", STORE), 1495)
		self.assertEqual(get_stock_balance("_Test Ketchup Pre-mix", "_Test Mixer Warehouse - _TC"), 1250)

		run_stage(work_order, 150, 105, output_qty=990)
		self.assertEqual(get_stock_balance("_Test Ketchup Pre-mix", "_Test Mixer Warehouse - _TC"), 0)
		self.assertEqual(get_stock_balance("_Test Cooked Ketchup Base", "_Test Kettle Warehouse - _TC"), 990)

		run_stage(work_order, 105, 45, output_qty=1975, rejected_qty=5)
		work_order.reload()
		self.assertEqual(work_order.status, "Completed")
		self.assertEqual(work_order.produced_qty, 1975)
		self.assertEqual(get_stock_balance("_Test Ketchup Bottle", FINISHED_GOODS), 1975)
		self.assertEqual(get_stock_balance("_Test Cooked Ketchup Base", "_Test Filler Warehouse - _TC"), 0)

		state = PlantRunState(PlantRun(work_order.name)).as_dict()
		self.assertEqual([stage.phase for stage in state.stages], ["done", "done", "done"])
		self.assertEqual(state.stages[1].output.process_loss_qty, 10)
		self.assertEqual(len(state.entries), 6)

	def test_consume_refuses_quantity_off_formula(self):
		plant_floor = make_ketchup_plant()
		stock_ketchup_materials()
		work_order = plant_floor.make_work_order(2000)
		with minutes_ago(60):
			run = PlantRun(work_order.name)
			run.start()
			job_card = run.active_job_card
			quantities = get_quantities(job_card, {"_Test Tomato Paste": 520})
			self.assertRaisesRegex(
				frappe.ValidationError, "4.0% off the formula", run.consume, job_card.name, quantities
			)

	def test_plant_builder_checks_unsaved_plant_and_reads_run(self):
		from erpnext.manufacturing.page.plant_builder.plant_builder import check_plant, get_run

		plant_floor = make_ketchup_plant()
		unsaved = plant_floor.as_dict()
		unsaved.update(name=None, floor_name="_Test Unsaved Plant", packing_materials=[])
		self.assertIn("Add at least one packing material", check_plant(unsaved)["errors"])

		run = get_run(plant_floor.make_work_order(2000).name)
		self.assertEqual([stage.phase for stage in run["stages"]], ["waiting", "waiting", "waiting"])
		self.assertEqual(run["plan"].input_weight, 1250)
		self.assertEqual(run["stages"][1]["items"][0].item_code, "_Test Ketchup Pre-mix")
		self.assertTrue(run["stages"][1]["items"][0].is_fixed)


def minutes_ago(minutes):
	return patch(
		"erpnext.manufacturing.doctype.work_order.services.plant_run.actions.now_datetime",
		return_value=add_to_date(now_datetime(), minutes=-minutes),
	)


def run_stage(work_order, start, end, output_qty, rejected_qty=0, actual=None):
	with minutes_ago(start):
		run = PlantRun(work_order.name)
		if run.work_order.docstatus == 0:
			run.start()
		job_card = run.active_job_card
		run.consume(job_card.name, get_quantities(job_card, actual or {}))

	with minutes_ago(end):
		PlantRun(work_order.name).produce(job_card.name, output_qty, rejected_qty)


def get_quantities(job_card, actual):
	return {row.item_code: actual.get(row.item_code, row.required_qty) for row in job_card.items}


def make_ketchup_items():
	for item_code, stock_uom in (
		("_Test Tomato Paste", "Kg"),
		("_Test Ketchup Sugar", "Kg"),
		("_Test Ketchup Pre-mix", "Kg"),
		("_Test Cooked Ketchup Base", "Kg"),
		("_Test Ketchup PET Bottle", "Nos"),
	):
		make_item(item_code, {"is_stock_item": 1, "stock_uom": stock_uom, "valuation_rate": 10})

	make_item(
		"_Test Process Water",
		{"is_stock_item": 1, "stock_uom": "Litre", "valuation_rate": 1},
		uoms=[{"uom": "Kg", "conversion_factor": 1}],
	)
	make_item(
		"_Test Ketchup Bottle",
		{"is_stock_item": 1, "stock_uom": "Nos", "weight_per_unit": 0.5, "weight_uom": "Kg"},
	)
	return "_Test Ketchup Bottle"


def make_machine(name, machine_model):
	workstation_type = f"_Test {name} Type"
	if not frappe.db.exists("Workstation Type", workstation_type):
		frappe.get_doc(
			{
				"doctype": "Workstation Type",
				"workstation_type": workstation_type,
				"machine_model": machine_model,
			}
		).insert()

	warehouse = create_warehouse(f"_Test {name} Warehouse")
	if not frappe.db.exists("Workstation", f"_Test {name}"):
		frappe.get_doc(
			{
				"doctype": "Workstation",
				"workstation_name": f"_Test {name}",
				"workstation_type": workstation_type,
				"warehouse": warehouse,
			}
		).insert()

	if not frappe.db.exists("Operation", f"_Test {name} Operation"):
		frappe.get_doc({"doctype": "Operation", "name": f"_Test {name} Operation"}).insert()

	return f"_Test {name}", f"_Test {name} Operation"


def make_ketchup_plant():
	production_item = make_ketchup_items()
	stages = []
	for name, machine_model, output, yield_percentage in (
		("Mixer", "Mixer", "_Test Ketchup Pre-mix", 100),
		("Kettle", "Steam Kettle", "_Test Cooked Ketchup Base", 80),
		("Filler", "Filling Line", None, 100),
	):
		workstation, operation = make_machine(name, machine_model)
		stages.append(
			{
				"stage_name": name,
				"workstation": workstation,
				"operation": operation,
				"semi_finished_good": output,
				"yield_percentage": yield_percentage,
				"time_in_mins": 30,
			}
		)

	frappe.delete_doc_if_exists("Plant Floor", "_Test Ketchup Plant")
	return frappe.get_doc(
		{
			"doctype": "Plant Floor",
			"floor_name": "_Test Ketchup Plant",
			"company": "_Test Company",
			"warehouse": STORE,
			"fg_warehouse": FINISHED_GOODS,
			"production_item": production_item,
			"batch_size": 2000,
			"formula_tolerance": 2,
			"materials": [
				{"item_code": "_Test Tomato Paste", "percentage": 40},
				{"item_code": "_Test Process Water", "is_balance_item": 1},
				{"item_code": "_Test Ketchup Sugar", "percentage": 30},
			],
			"stages": stages,
			"packing_materials": [{"item_code": "_Test Ketchup PET Bottle", "qty_per_unit": 1}],
		}
	).insert()


def stock_ketchup_materials():
	for item_code, qty in (
		("_Test Tomato Paste", 2000),
		("_Test Process Water", 2000),
		("_Test Ketchup Sugar", 2000),
		("_Test Ketchup PET Bottle", 3000),
	):
		make_stock_entry(item_code=item_code, target=STORE, qty=qty, basic_rate=10)


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
