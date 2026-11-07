# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.utils import add_to_date, now_datetime

from erpnext.manufacturing.doctype.bom_creator.test_process_design import (
	FINISHED_GOODS,
	STORE,
	make_ketchup_bom,
	make_ketchup_design,
	make_parallel_ketchup_design,
	make_process_work_order,
	stock_ketchup_materials,
)
from erpnext.manufacturing.doctype.work_order.services.plant_run.actions import MachineBusyError, PlantRun
from erpnext.manufacturing.doctype.work_order.services.plant_run.lot import Lot
from erpnext.manufacturing.doctype.work_order.services.plant_run.picks import (
	PickedSerialBatch,
	get_pick_options,
)
from erpnext.manufacturing.doctype.work_order.services.plant_run.state import PlantRunState
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.doctype.work_order.work_order import close_work_order
from erpnext.setup.doctype.employee.test_employee import make_employee
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.utils import get_stock_balance
from erpnext.tests.utils import ERPNextTestSuite


class TestPlantRun(ERPNextTestSuite):
	def test_work_order_from_process_bom_has_stages_and_machine_warehouses(self):
		work_order = make_ketchup_work_order()

		self.assertTrue(work_order.track_semi_finished_goods)
		self.assertEqual(
			[(row.finished_good, row.output_qty, row.sequence_id) for row in work_order.operations],
			[
				("_Test Ketchup Pre-mix", 1250, 1),
				("_Test Cooked Ketchup Base", 1000, 2),
				("_Test Ketchup Bottle", 0, 3),
			],
		)
		self.assertEqual(work_order.operations[1].wip_warehouse, "_Test Kettle Warehouse - _TC")
		required = {(row.operation_row_id, row.item_code): row for row in work_order.required_items}
		self.assertEqual(required[(1, "_Test Tomato Paste")].required_qty, 500)
		self.assertEqual(
			required[(2, "_Test Ketchup Pre-mix")].source_warehouse, "_Test Mixer Warehouse - _TC"
		)
		self.assertEqual(required[(3, "_Test Ketchup PET Bottle")].source_warehouse, STORE)

	def test_run_changes_quantity_before_it_starts(self):
		from erpnext.manufacturing.page.plant_builder.plant_builder import set_run_qty

		work_order = make_ketchup_work_order()
		set_run_qty(work_order.name, 1000)

		work_order.reload()
		required = {(row.operation_row_id, row.item_code): row for row in work_order.required_items}
		self.assertEqual(required[(1, "_Test Tomato Paste")].required_qty, 250)
		self.assertEqual(work_order.operations[1].output_qty, 500)

	def test_run_needs_an_item_at_each_operation(self):
		work_order = make_wo_order_test_record(qty=1, do_not_submit=True)
		self.assertRaisesRegex(frappe.ValidationError, "does not make an item", PlantRun, work_order.name)

	def test_run_moves_stock_through_machines(self):
		stock_ketchup_materials()
		work_order = make_ketchup_work_order()

		run_stage(work_order, 180, 150, output_qty=1250, actual={"_Test Tomato Paste": 505})
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
		self.assertEqual(state.stages[1].output.weight_factor, 1)
		self.assertEqual(len(state.entries), 6)
		cooked = next(
			entry
			for entry in state.entries
			if entry.purpose == "Manufacture" and entry.job_card == state.stages[1].job_card.name
		)
		finished = next(row for row in cooked["items"] if row.is_finished_item)
		self.assertTrue(finished.batch_ids[0].startswith("_TKB-"))

	def test_last_lot_tops_up_a_fraction_of_a_unit_lost_to_rounding(self):
		stock_ketchup_materials()
		work_order = make_ketchup_work_order()
		run_stage(work_order, 180, 150, output_qty=1250)
		run_stage(work_order, 150, 105, output_qty=990.333)
		run_stage(work_order, 105, 45, output_qty=1975, rejected_qty=5)

		work_order.reload()
		self.assertEqual((work_order.status, work_order.produced_qty), ("Completed", 1975))
		self.assertEqual(work_order.process_loss_qty, 25.34)

	def test_lot_preview_plans_materials_and_lists_errors(self):
		stock_ketchup_materials()
		work_order = make_ketchup_work_order()
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
		stock_ketchup_materials()
		work_order = make_ketchup_work_order()
		with minutes_ago(60):
			run = PlantRun(work_order.name)
			run.start()
			job_card = run.get_open_job_card(1)
			quantities = get_quantities(run, job_card, {"_Test Tomato Paste": 520})
			self.assertRaisesRegex(
				frappe.ValidationError, "4.0% off the formula", run.consume, job_card.name, quantities
			)

	def test_produce_refuses_more_than_the_lot_quantity(self):
		stock_ketchup_materials()
		work_order = make_ketchup_work_order()
		with minutes_ago(60):
			run = PlantRun(work_order.name)
			run.start()
			job_card = run.get_open_job_card(1)
			run.consume(job_card.name, get_quantities(run, job_card, {}))

		self.assertRaisesRegex(
			frappe.ValidationError,
			"You cannot make more than 1250",
			PlantRun(work_order.name).produce,
			job_card.name,
			1251,
		)

	def test_plant_builder_reads_the_run_from_the_work_order(self):
		from erpnext.manufacturing.page.plant_builder.plant_builder import get_run

		run = get_run(make_ketchup_work_order().name)
		self.assertEqual([stage.phase for stage in run["stages"]], ["waiting", "waiting", "waiting"])
		self.assertEqual(run["plan"].input_weight, 1250)
		self.assertEqual(run["stages"][1]["items"][0].item_code, "_Test Ketchup Pre-mix")
		self.assertTrue(run["stages"][1]["items"][0].is_input)
		plant = run["plant"]["doc"]
		self.assertEqual([stage.yield_percentage for stage in plant.stages], [100, 80, 100])
		materials = {row.item_code: row for row in plant.materials}
		self.assertEqual(materials["_Test Process Water"].percentage, 30)
		self.assertTrue(materials["_Test Process Water"].is_balance_item)
		self.assertEqual(plant.packing_materials[0].qty_per_unit, 1)

	def test_plant_builder_run_follows_work_order_permissions(self):
		from erpnext.manufacturing.page.plant_builder.plant_builder import get_run, set_run_qty

		work_order = make_ketchup_work_order()
		outsider = create_user("plant-builder-outsider@example.com", "Accounts User")
		with self.set_user(outsider.name):
			self.assertRaises(frappe.PermissionError, get_run, work_order.name)

		reader = create_user("plant-builder-stock-user@example.com", "Stock User")
		with self.set_user(reader.name):
			self.assertTrue(frappe.has_permission("Work Order", "read", doc=work_order.name))
			self.assertTrue(get_run(work_order.name)["stages"])
			self.assertRaises(frappe.PermissionError, set_run_qty, work_order.name, 1000)

		self.assertEqual(frappe.db.get_value("Work Order", work_order.name, "qty"), 2000)

	def test_consume_uses_the_picked_batches(self):
		run, job_card, quantities, sugar = start_with_sugar_batches()

		options = run.get_pick_options(job_card.name, sugar.name)
		self.assertEqual(
			[(row["batch_id"], row["qty"]) for row in options["batches"]],
			[("_TKS-PICK-A", 300), ("_TKS-PICK-B", 300)],
		)

		first, second = (row["batch_no"] for row in options["batches"])
		qty = quantities[sugar.name]
		picks = {sugar.name: {"batches": {first: qty - 100, second: 100}}}
		entry = frappe.get_doc("Stock Entry", run.consume(job_card.name, quantities, picks))

		row = next(row for row in entry.items if row.item_code == "_Test Ketchup Sugar")
		bundle = frappe.get_doc("Serial and Batch Bundle", row.serial_and_batch_bundle)
		self.assertEqual(
			sorted((entry.batch_no, entry.qty) for entry in bundle.entries),
			sorted([(first, -(qty - 100)), (second, -100)]),
		)

	def test_consume_refuses_picked_batches_off_the_quantity(self):
		run, job_card, quantities, sugar = start_with_sugar_batches()

		batch_no = frappe.db.get_value("Batch", {"batch_id": "_TKS-PICK-A"})
		picks = {sugar.name: {"batches": {batch_no: 100}}}
		self.assertRaisesRegex(frappe.ValidationError, "Pick", run.consume, job_card.name, quantities, picks)

	def test_picked_serial_nos_make_the_outward_bundle(self):
		item = make_item("_Test Plant Run Serial Part", {"is_stock_item": 1, "has_serial_no": 1}).name
		make_stock_entry(
			item_code=item,
			target=STORE,
			qty=3,
			basic_rate=10,
			serial_no="_TPRS-1\n_TPRS-2\n_TPRS-3",
			use_serial_batch_fields=1,
		)
		serial_nos = sorted(row["serial_no"] for row in get_pick_options(item, STORE)["serial_nos"])
		self.assertEqual(len(serial_nos), 3)

		entry = make_stock_entry(
			item_code=item,
			source=STORE,
			target="_Test Warehouse - _TC",
			qty=2,
			purpose="Material Transfer",
			do_not_save=True,
		)
		entry.items[0].job_card_item = "picked-row"
		PickedSerialBatch(entry, {"picked-row": {"serial_nos": serial_nos[1:]}}).apply()
		entry.insert()
		entry.submit()

		bundle = frappe.get_doc("Serial and Batch Bundle", entry.items[0].serial_and_batch_bundle)
		self.assertEqual(sorted(row.serial_no for row in bundle.entries), serial_nos[1:])

	def test_next_stage_waits_while_its_machine_is_busy(self):
		stock_ketchup_materials()
		bom = make_ketchup_bom(make_ketchup_design())
		first = make_process_work_order(bom, 1000)
		second = make_process_work_order(bom, 1000)

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

	def test_stage_waits_while_capacity_planning_reserves_its_machine(self):
		stock_ketchup_materials()
		bom = make_ketchup_bom(make_ketchup_design())
		with self.change_settings("Manufacturing Settings", {"disable_capacity_planning": 0}):
			first = make_process_work_order(bom, 1000)
			first.submit()
			second = make_process_work_order(bom, 1000)
			PlantRun(second.name).start()

			mixer = PlantRun(second.name).get_open_job_card(1)
			self.assertFalse(mixer.time_logs)
			self.assertRaisesRegex(MachineBusyError, "reserved", PlantRun(second.name).start, mixer.name)

	def test_parallel_stages_feed_the_stage_after_them(self):
		work_order = make_process_work_order(make_ketchup_bom(make_parallel_ketchup_design()), 2000)
		stock_ketchup_materials()
		make_stock_entry(item_code="_Test Ketchup Spices", target=STORE, qty=100, basic_rate=10)
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
		stock_ketchup_materials()
		work_order = make_ketchup_work_order()
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
		stock_ketchup_materials()
		work_order = make_ketchup_work_order()
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
		stock_ketchup_materials()
		work_order = make_ketchup_work_order()
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
		stock_ketchup_materials()
		work_order = make_ketchup_work_order()
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
		work_order = make_ketchup_work_order()
		with minutes_ago(60):
			PlantRun(work_order.name).start()
		job_card = PlantRun(work_order.name).get_open_job_card(1)
		with minutes_ago(50):
			PlantRun(work_order.name).report_breakdown(job_card.name)

		close_work_order(work_order.name, "Closed")

		self.assertEqual(frappe.db.get_value("Job Card", job_card.name, "status"), "Cancelled")
		self.assertEqual(frappe.db.get_value("Workstation", "_Test Mixer", "status"), "Off")


def make_ketchup_work_order(qty=2000):
	return make_process_work_order(make_ketchup_bom(make_ketchup_design()), qty)


def start_with_sugar_batches():
	stock_ketchup_materials()
	frappe.db.set_value("Item", "_Test Ketchup Sugar", "has_batch_no", 1)
	frappe.clear_document_cache("Item", "_Test Ketchup Sugar")
	for batch_id in ("_TKS-PICK-A", "_TKS-PICK-B"):
		batch = frappe.get_doc({"doctype": "Batch", "batch_id": batch_id, "item": "_Test Ketchup Sugar"})
		make_stock_entry(
			item_code="_Test Ketchup Sugar",
			target=STORE,
			qty=300,
			basic_rate=10,
			batch_no=batch.insert().name,
		)

	work_order = make_ketchup_work_order()
	run = PlantRun(work_order.name)
	run.start()
	job_card = run.get_open_job_card(1)
	quantities = get_quantities(run, job_card, {})
	sugar = next(row for row in job_card.items if row.item_code == "_Test Ketchup Sugar")
	return run, job_card, quantities, sugar


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
