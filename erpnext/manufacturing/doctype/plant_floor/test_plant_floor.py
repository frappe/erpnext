# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.permissions import add_user_permission
from frappe.utils import add_to_date, now_datetime

from erpnext.manufacturing.doctype.plant_floor.plant_floor import get_stock_summary
from erpnext.manufacturing.doctype.work_order.services.plant_run.actions import MachineBusyError, PlantRun
from erpnext.manufacturing.doctype.work_order.services.plant_run.lot import Lot
from erpnext.manufacturing.doctype.work_order.services.plant_run.state import PlantRunState
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.doctype.work_order.work_order import close_work_order
from erpnext.manufacturing.page.shop_floor.shop_floor import get_work_orders
from erpnext.setup.doctype.employee.test_employee import make_employee
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

	def test_work_order_company_must_match_plant_floor(self):
		plant_floor = make_ketchup_plant()
		work_order = frappe.new_doc("Work Order")
		work_order.update(
			{
				"production_item": plant_floor.production_item,
				"plant_floor": plant_floor.name,
				"company": "_Test Company 1",
				"qty": 10,
			}
		)
		self.assertRaisesRegex(frappe.ValidationError, "belongs to company", work_order.insert)

		work_order = plant_floor.make_work_order(10)
		work_order.company = "_Test Company 1"
		self.assertRaisesRegex(frappe.ValidationError, "belongs to company", work_order.save)

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
		self.assertEqual(work_order.process_loss_qty, 25)
		self.assertEqual(get_stock_balance("_Test Ketchup Bottle", FINISHED_GOODS), 1975)
		self.assertEqual(get_stock_balance("_Test Cooked Ketchup Base", "_Test Filler Warehouse - _TC"), 0)

		state = PlantRunState(PlantRun(work_order.name)).as_dict()
		self.assertEqual([stage.phase for stage in state.stages], ["done", "done", "done"])
		self.assertEqual(state.stages[1].output.process_loss_qty, 10)
		self.assertEqual(len(state.entries), 6)
		cooked = next(
			entry
			for entry in state.entries
			if entry.purpose == "Manufacture" and entry.job_card == state.stages[1].job_card.name
		)
		finished = next(row for row in cooked["items"] if row.is_finished_item)
		self.assertTrue(finished.batch_ids[0].startswith("_TKB-"))

	def test_last_lot_tops_up_a_fraction_of_a_unit_lost_to_rounding(self):
		plant_floor = make_ketchup_plant()
		stock_ketchup_materials()
		work_order = plant_floor.make_work_order(2000)
		run_stage(work_order, 180, 150, output_qty=1250)
		run_stage(work_order, 150, 105, output_qty=990.333)
		run_stage(work_order, 105, 45, output_qty=1975, rejected_qty=5)

		work_order.reload()
		self.assertEqual((work_order.status, work_order.produced_qty), ("Completed", 1975))
		self.assertEqual(work_order.process_loss_qty, 25.34)

	def test_lot_preview_plans_materials_and_lists_errors(self):
		plant_floor = make_ketchup_plant()
		stock_ketchup_materials()
		work_order = plant_floor.make_work_order(2000)
		with minutes_ago(60):
			PlantRun(work_order.name).start()
		job_card = PlantRun(work_order.name).get_open_job_card(1)
		rows = {row.item_code: row.name for row in job_card.items}

		preview = PlantRun(work_order.name).preview(job_card.name, {})
		self.assertEqual((preview.output_qty, preview.errors), (1250, []))
		self.assertEqual(preview["items"][rows["_Test Tomato Paste"]].qty, 500)

		preview = PlantRun(work_order.name).preview(job_card.name, {rows["_Test Tomato Paste"]: 520})
		self.assertIn(
			"_Test Tomato Paste is 4.0% off the formula. The allowed range is ±2.0%.", preview.errors
		)
		self.assertTrue(preview["items"][rows["_Test Tomato Paste"]].is_off)
		self.assertEqual(preview["items"][rows["_Test Process Water"]].qty, 355)

	def test_consume_refuses_quantity_off_formula(self):
		plant_floor = make_ketchup_plant()
		stock_ketchup_materials()
		work_order = plant_floor.make_work_order(2000)
		with minutes_ago(60):
			run = PlantRun(work_order.name)
			run.start()
			job_card = run.get_open_job_card(1)
			quantities = get_quantities(run, job_card, {"_Test Tomato Paste": 520})
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
		self.assertTrue(run["stages"][1]["items"][0].is_input)

	def test_plant_builder_check_needs_workstation_read(self):
		from erpnext.manufacturing.page.plant_builder.plant_builder import check_plant

		workstation, operation = make_machine("Mixer", "Mixer")
		unsaved = {
			"floor_name": "_Test Unsaved Plant",
			"stages": [{"stage_name": "Mixer", "workstation": workstation, "operation": operation}],
		}
		self.assertIn(workstation, check_plant(unsaved)["machines"])

		user = create_user("plant-builder-manager@example.com", "Manufacturing Manager")
		with self.set_user(user.name):
			self.assertTrue(frappe.has_permission("Plant Floor", "read"))
			self.assertRaises(frappe.PermissionError, check_plant, unsaved)

	def test_plant_builder_run_needs_plant_floor_read(self):
		from erpnext.manufacturing.page.plant_builder.plant_builder import get_run, preview_lot

		work_order = make_ketchup_plant().make_work_order(2000)
		PlantRun(work_order.name).start()
		job_card = PlantRun(work_order.name).get_open_job_card(1)
		user = create_user("plant-builder-stock-user@example.com", "Stock User")
		with self.set_user(user.name):
			self.assertTrue(frappe.has_permission("Work Order", "read", doc=work_order.name))
			self.assertRaises(frappe.PermissionError, get_run, work_order.name)
			self.assertRaises(frappe.PermissionError, preview_lot, work_order.name, job_card.name)

	def test_plant_builder_action_checks_plant_floor_read_before_it_runs(self):
		from erpnext.manufacturing.page.plant_builder.plant_builder import set_run_qty

		work_order = make_ketchup_plant().make_work_order(2000)
		if not frappe.db.exists("Plant Floor", "_Test Other Plant"):
			frappe.get_doc({"doctype": "Plant Floor", "floor_name": "_Test Other Plant"}).insert()
		user = create_user("plant-builder-other-plant@example.com", "Manufacturing User")
		add_user_permission("Plant Floor", "_Test Other Plant", user.name, applicable_for="Plant Floor")
		with self.set_user(user.name):
			self.assertTrue(frappe.has_permission("Work Order", "write", doc=work_order.name))
			self.assertRaises(frappe.PermissionError, set_run_qty, work_order.name, 1000)

		self.assertEqual(frappe.db.get_value("Work Order", work_order.name, "qty"), 2000)

	def test_plant_builder_save_numbers_stages_by_position(self):
		from erpnext.manufacturing.page.plant_builder.plant_builder import (
			check_plant,
			get_plant,
			make_work_order,
			save_plant,
		)

		plant_floor = make_ketchup_plant()
		make_item("_Test Cooled Ketchup Base", {"is_stock_item": 1, "stock_uom": "Kg", "valuation_rate": 10})
		workstation, operation = make_machine("Cooler", "Cooler")
		doc = get_plant(plant_floor.name)["doc"]
		insert_stage(
			doc,
			2,
			{
				"stage_name": "Cooler",
				"workstation": workstation,
				"operation": operation,
				"semi_finished_good": "_Test Cooled Ketchup Base",
				"yield_percentage": 100,
				"time_in_mins": 30,
			},
		)
		self.assertEqual(get_plan_stages(check_plant(doc)), ["Mixer", "Kettle", "Cooler", "Filler"])
		result = save_plant(doc)
		self.assertEqual(result["errors"], [])
		self.assertEqual(get_plan_stages(result), ["Mixer", "Kettle", "Cooler", "Filler"])
		work_order = frappe.get_doc("Work Order", make_work_order(plant_floor.name, 2000))
		self.assertEqual(
			[(row.description, row.finished_good) for row in work_order.operations],
			[
				("Mixer", "_Test Ketchup Pre-mix"),
				("Kettle", "_Test Cooked Ketchup Base"),
				("Cooler", "_Test Cooled Ketchup Base"),
				("Filler", "_Test Ketchup Bottle"),
			],
		)

		doc = get_plant(plant_floor.name)["doc"]
		remove_stage(doc, 0)
		result = save_plant(doc)
		self.assertEqual(result["errors"], [])
		self.assertEqual(get_plan_stages(result), ["Kettle", "Cooler", "Filler"])
		work_order = frappe.get_doc("Work Order", make_work_order(plant_floor.name, 2000))
		self.assertEqual([row.description for row in work_order.operations], ["Kettle", "Cooler", "Filler"])
		self.assertEqual(
			{row.item_code for row in work_order.required_items if row.operation_row_id == 1},
			{"_Test Tomato Paste", "_Test Process Water", "_Test Ketchup Sugar"},
		)

	def test_next_stage_waits_while_its_machine_is_busy(self):
		plant_floor = make_ketchup_plant()
		stock_ketchup_materials()
		first = plant_floor.make_work_order(1000)
		second = plant_floor.make_work_order(1000)

		run_stage(first, 240, 220, output_qty=625)
		with minutes_ago(215):
			run = PlantRun(first.name)
			job_card = run.get_open_job_card(2)
			run.consume(job_card.name, get_quantities(run, job_card, {}))

		run_stage(second, 210, 200, output_qty=625)
		self.assertEqual(PlantRunState(PlantRun(second.name)).as_dict().stages[1].phase, "waiting")
		self.assertRaises(MachineBusyError, PlantRun(second.name).start)

		with minutes_ago(150):
			PlantRun(first.name).produce(job_card.name, 500)
		with minutes_ago(140):
			PlantRun(second.name).start()
		self.assertEqual(PlantRunState(PlantRun(second.name)).as_dict().stages[1].phase, "ready")

	def test_parallel_stages_feed_the_stage_after_them(self):
		plant_floor = make_parallel_ketchup_plant()
		self.assertEqual(plant_floor.setup_errors, [])
		plan = plant_floor.get_batch_plan(2000).as_dict()
		self.assertEqual(plan.input_weight, 1250)
		self.assertEqual([row.sequence_id for row in plan.stages], [1, 1, 2, 3])
		self.assertEqual(
			[(row.item_code, row.qty) for row in plan.stages[2].inputs],
			[("_Test Ketchup Spice Mix", 62.5), ("_Test Ketchup Pre-mix", 1187.5)],
		)

		stock_ketchup_materials()
		make_stock_entry(item_code="_Test Ketchup Spices", target=STORE, qty=100, basic_rate=10)
		work_order = plant_floor.make_work_order(2000)
		self.assertEqual([row.sequence_id for row in work_order.operations], [1, 1, 2, 3])
		with minutes_ago(200):
			PlantRun(work_order.name).start()
		phases = [stage.phase for stage in PlantRunState(PlantRun(work_order.name)).as_dict().stages]
		self.assertEqual(phases, ["ready", "ready", "waiting", "waiting"])

		run_stage(work_order, 190, 160, output_qty=62.5, stage=1)
		self.assertFalse(PlantRun(work_order.name).get_open_job_card(3).time_logs)
		run_stage(work_order, 180, 150, output_qty=1187.5, stage=2)
		kettle = PlantRun(work_order.name).get_open_job_card(3)
		self.assertTrue(kettle.time_logs)
		self.assertEqual(
			{(row.item_code, row.source_warehouse) for row in kettle.items},
			{
				("_Test Ketchup Spice Mix", "_Test Mill Warehouse - _TC"),
				("_Test Ketchup Pre-mix", "_Test Mixer Warehouse - _TC"),
			},
		)

		run_stage(work_order, 140, 100, output_qty=1000, stage=3)
		run_stage(work_order, 90, 60, output_qty=2000, stage=4)
		work_order.reload()
		self.assertEqual(work_order.status, "Completed")
		self.assertEqual(get_stock_balance("_Test Ketchup Spice Mix", "_Test Mill Warehouse - _TC"), 0)
		self.assertEqual(get_stock_balance("_Test Ketchup Bottle", FINISHED_GOODS), 2000)

	def test_next_stage_takes_part_of_the_semi_finished_goods(self):
		plant_floor = make_ketchup_plant()
		stock_ketchup_materials()
		work_order = plant_floor.make_work_order(2000)
		run_stage(work_order, 300, 270, output_qty=1250)
		run_stage(work_order, 260, 230, output_qty=400, actual={"_Test Ketchup Pre-mix": 500}, stage=2)

		kettle, filler = PlantRunState(PlantRun(work_order.name)).as_dict().stages[1:]
		self.assertEqual((kettle.lot, kettle.phase, kettle.inputs[0].waiting_qty), (2, "ready", 750))
		self.assertEqual((filler.lot, filler.phase, filler.inputs[0].waiting_qty), (1, "ready", 400))

		run_stage(work_order, 220, 200, output_qty=800, stage=3)
		run_stage(work_order, 190, 160, output_qty=600, stage=2)
		run_stage(work_order, 150, 120, output_qty=1200, stage=3)

		work_order.reload()
		self.assertEqual((work_order.status, work_order.produced_qty), ("Completed", 2000))
		self.assertEqual(get_stock_balance("_Test Ketchup PET Bottle", STORE), 1000)
		state = PlantRunState(PlantRun(work_order.name)).as_dict()
		self.assertEqual(
			[(stage.phase, stage.lot) for stage in state.stages], [("done", 1), ("done", 2), ("done", 2)]
		)
		self.assertEqual(state.stages[1].output.completed_qty, 1000)

	def test_entry_log_lists_a_row_once_for_all_its_batches(self):
		plant_floor = make_ketchup_plant()
		stock_ketchup_materials()
		work_order = plant_floor.make_work_order(2000)
		run_stage(work_order, 300, 270, output_qty=1250)
		run_stage(work_order, 260, 230, output_qty=400, actual={"_Test Ketchup Pre-mix": 500}, stage=2)
		run_stage(work_order, 220, 190, output_qty=600, stage=2)
		run_stage(work_order, 180, 150, output_qty=2000, stage=3)

		state = PlantRunState(PlantRun(work_order.name)).as_dict()
		transfer = next(
			entry
			for entry in state.entries
			if entry.purpose == "Material Transfer for Manufacture"
			and entry.job_card == state.stages[2].job_card.name
		)
		rows = [row for row in transfer["items"] if row.item_code == "_Test Cooked Ketchup Base"]
		self.assertEqual([row.qty for row in rows], [1000])
		self.assertEqual(len(rows[0].batch_ids), 2)

	def test_partial_lots_of_whole_units_add_up_to_the_work_order(self):
		plant_floor = make_ketchup_plant()
		stock_ketchup_materials()
		work_order = plant_floor.make_work_order(2000)
		run_stage(work_order, 300, 270, output_qty=1250)
		run_stage(work_order, 260, 230, output_qty=1000)

		run_stage(work_order, 220, 200, output_qty=666, actual={"_Test Cooked Ketchup Base": 333.3}, stage=3)
		filler = PlantRunState(PlantRun(work_order.name)).as_dict().stages[2]
		self.assertEqual((filler.inputs[0].waiting_qty, filler.output.done_qty), (666.7, 666))
		run_stage(work_order, 190, 160, output_qty=1334, stage=3)

		work_order.reload()
		self.assertEqual((work_order.status, work_order.produced_qty), ("Completed", 2000))
		self.assertEqual(get_stock_balance("_Test Ketchup PET Bottle", STORE), 1000)

	def test_breakdown_stops_the_machine_and_restart_makes_downtime_entry(self):
		plant_floor = make_ketchup_plant()
		stock_ketchup_materials()
		work_order = plant_floor.make_work_order(2000)
		operator = make_employee("plant.operator@example.com", company="_Test Company")
		with minutes_ago(60):
			PlantRun(work_order.name).start()
		job_card = PlantRun(work_order.name).get_open_job_card(1)

		with minutes_ago(50):
			PlantRun(work_order.name).report_breakdown(job_card.name)
		state = PlantRunState(PlantRun(work_order.name)).as_dict()
		self.assertEqual(frappe.db.get_value("Workstation", "_Test Mixer", "status"), "Problem")
		self.assertTrue(state.stages[0].breakdown)
		self.assertFalse(state.work_order["is_paused"])

		with minutes_ago(45):
			PlantRun(work_order.name).resume()
		self.assertTrue(frappe.db.get_value("Job Card", job_card.name, "is_paused"))

		with minutes_ago(30):
			downtime = PlantRun(work_order.name).restart_machine(
				job_card.name, "Machine malfunction", "Replaced the agitator belt", operator
			)
		downtime = frappe.get_doc("Downtime Entry", downtime)
		self.assertEqual((downtime.workstation, round(downtime.downtime)), ("_Test Mixer", 20))
		self.assertEqual(frappe.db.get_value("Workstation", "_Test Mixer", "status"), "Production")
		self.assertFalse(frappe.db.get_value("Job Card", job_card.name, "is_paused"))

	def test_closing_work_order_clears_the_machine_breakdown(self):
		plant_floor = make_ketchup_plant()
		work_order = plant_floor.make_work_order(2000)
		with minutes_ago(60):
			PlantRun(work_order.name).start()
		job_card = PlantRun(work_order.name).get_open_job_card(1)
		with minutes_ago(50):
			PlantRun(work_order.name).report_breakdown(job_card.name)

		close_work_order(work_order.name, "Closed")

		self.assertEqual(frappe.db.get_value("Job Card", job_card.name, "status"), "Cancelled")
		self.assertEqual(frappe.db.get_value("Workstation", "_Test Mixer", "status"), "Off")

	def test_setup_errors_for_parallel_stages(self):
		plant_floor = make_parallel_ketchup_plant()
		plant_floor.stages[2].sequence_id = 3
		plant_floor.stages[3].sequence_id = 3
		plant_floor.materials[0].stage_row_id = 4
		plant_floor.materials[3].stage_row_id = 2
		errors = plant_floor.setup_errors

		self.assertIn("Stage 3 needs Sequence ID 1 or 2", errors)
		self.assertIn("The packing stage runs on its own, after all other stages", errors)
		self.assertIn(
			"Raw material _Test Tomato Paste goes into stage 4, which is not a process stage", errors
		)
		self.assertIn("Stage 1 starts the process, so give it at least one raw material", errors)


def minutes_ago(minutes):
	return patch(
		"erpnext.manufacturing.doctype.work_order.services.plant_run.actions.now_datetime",
		return_value=add_to_date(now_datetime(), minutes=-minutes),
	)


def run_stage(work_order, start, end, output_qty, rejected_qty=0, actual=None, stage=None):
	with minutes_ago(start):
		run = PlantRun(work_order.name)
		if run.work_order.docstatus == 0:
			run.start()
		job_card = run.get_open_job_card(stage or get_next_stage(run))
		if not job_card.time_logs:
			run.start(job_card.name)
		run.consume(job_card.name, get_quantities(run, job_card, actual or {}))

	with minutes_ago(end):
		PlantRun(work_order.name).produce(job_card.name, output_qty, rejected_qty)


def insert_stage(doc, index, stage):
	doc.stages.insert(index, frappe._dict(stage))
	set_stage_numbers(doc, lambda no: no + 1 if no > index else no)


def remove_stage(doc, index):
	doc.stages.pop(index)
	set_stage_numbers(doc, lambda no: 1 if no == index + 1 else no - 1 if no > index + 1 else no)


def set_stage_numbers(doc, stage_of):
	for row in doc.materials:
		row.stage_row_id = stage_of(row.stage_row_id or 1)
	for sequence_id, stage in enumerate(doc.stages, start=1):
		stage.sequence_id = sequence_id


def get_plan_stages(result):
	return [stage.stage_name for stage in result["plan"].stages]


def get_next_stage(run):
	flow = run.get_flow()
	return next(row.idx for row in flow.stages if flow.get_open_card(row.idx) and flow.has_input(row.idx))


def get_quantities(run, job_card, actual):
	flow = run.get_flow()
	waiting = {
		(row.item_code, row.warehouse): row.waiting_qty for row in flow.get_inputs(job_card.operation_row_id)
	}
	passed = {
		row.name: actual.get(row.item_code, waiting[(row.item_code, row.source_warehouse)])
		for row in job_card.items
		if (row.item_code, row.source_warehouse) in waiting
	}
	lot = Lot(flow, job_card, passed)
	return {
		row.name: actual.get(row.item_code, passed.get(row.name, lot.get_planned_qty(row)))
		for row in job_card.items
	}


def make_ketchup_items():
	for item_code, stock_uom in (
		("_Test Tomato Paste", "Kg"),
		("_Test Ketchup Sugar", "Kg"),
		("_Test Ketchup Pre-mix", "Kg"),
		("_Test Ketchup PET Bottle", "Nos"),
	):
		make_item(item_code, {"is_stock_item": 1, "stock_uom": stock_uom, "valuation_rate": 10})

	make_item(
		"_Test Cooked Ketchup Base",
		{
			"is_stock_item": 1,
			"stock_uom": "Kg",
			"valuation_rate": 10,
			"has_batch_no": 1,
			"create_new_batch": 1,
			"batch_number_series": "_TKB-.#####",
		},
	)

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


def make_parallel_ketchup_plant():
	for item_code in ("_Test Ketchup Spices", "_Test Ketchup Spice Mix"):
		make_item(item_code, {"is_stock_item": 1, "stock_uom": "Kg", "valuation_rate": 10})
	workstation, operation = make_machine("Mill", "Mill")

	plant_floor = make_ketchup_plant()
	plant_floor.append(
		"stages",
		{
			"stage_name": "Mill",
			"workstation": workstation,
			"operation": operation,
			"semi_finished_good": "_Test Ketchup Spice Mix",
			"yield_percentage": 100,
			"time_in_mins": 30,
		},
	)
	plant_floor.stages = [plant_floor.stages[-1], *plant_floor.stages[:-1]]
	for idx, (stage, sequence_id) in enumerate(zip(plant_floor.stages, (1, 1, 2, 3), strict=True), start=1):
		stage.idx, stage.sequence_id = idx, sequence_id

	for row in plant_floor.materials:
		row.stage_row_id = 2
	plant_floor.materials[2].percentage = 25
	plant_floor.append("materials", {"item_code": "_Test Ketchup Spices", "percentage": 5, "stage_row_id": 1})
	plant_floor.save()
	return plant_floor


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
