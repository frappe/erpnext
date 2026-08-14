# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import change_settings
from frappe.utils import add_to_date, get_datetime

from erpnext.manufacturing.doctype.job_card.job_card import OverlapError
from erpnext.manufacturing.doctype.production_plan.test_production_plan import (
	create_production_plan,
	make_bom,
)
from erpnext.manufacturing.doctype.work_order.test_work_order import make_operation, make_workstation
from erpnext.manufacturing.scheduling import loaders
from erpnext.manufacturing.scheduling.plan_adapter import apply_schedule, get_schedule_preview
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.tests.utils import ERPNextTestSuite


class TestPlanAdapter(ERPNextTestSuite):
	def setUp(self):
		super().setUp()
		self.workstation = "Test PPS WS"
		if not frappe.db.exists("Workstation", self.workstation):
			make_workstation(workstation=self.workstation, production_capacity=1)

		self.operation = "Test PPS Op"
		if not frappe.db.exists("Operation", self.operation):
			make_operation(operation=self.operation, workstation=self.workstation)

		for item in ["Test PPS FG", "Test PPS FG 2", "Test PPS SA 1", "Test PPS SA 2", "Test PPS RM"]:
			create_item(item, valuation_rate=100)

		for sub_assembly in ["Test PPS SA 1", "Test PPS SA 2"]:
			self.make_bom_with_operation(sub_assembly, ["Test PPS RM"], time_in_mins=60)

		self.make_bom_with_operation("Test PPS FG", ["Test PPS SA 1", "Test PPS SA 2"], time_in_mins=30)
		self.make_bom_with_operation("Test PPS FG 2", ["Test PPS RM"], time_in_mins=30)

	def make_bom_with_operation(self, item, raw_materials, time_in_mins, operations=None, batch_size=0):
		if frappe.db.exists("BOM", {"item": item, "docstatus": 1}):
			return

		bom = make_bom(item=item, raw_materials=raw_materials, with_operations=1, do_not_save=True)
		for operation in operations or [self.operation]:
			bom.append(
				"operations",
				{
					"operation": operation,
					"workstation": self.workstation,
					"time_in_mins": time_in_mins,
					"hour_rate": 100,
					"batch_size": batch_size,
				},
			)
		bom.insert(ignore_permissions=True)
		bom.submit()

	def make_plan(self):
		plan = create_production_plan(
			item_code="Test PPS FG",
			planned_qty=2,
			use_multi_level_bom=1,
			do_not_submit=True,
			skip_getting_mr_items=True,
		)
		plan.get_sub_assembly_items()
		plan.submit()
		return plan

	@change_settings(
		"Manufacturing Settings",
		{"mins_between_operations": 10, "allow_overtime": 0, "disable_capacity_planning": 0},
	)
	def test_job_cards_match_plan_schedule(self):
		plan = self.make_plan()
		start_date = get_datetime("2026-10-01 09:00:00")
		apply_schedule(plan.name, start_date)

		plan.reload()
		plan.make_work_order()
		work_orders = frappe.get_all("Work Order", filters={"production_plan": plan.name}, pluck="name")
		self.assertEqual(len(work_orders), 3)

		for name in work_orders:
			work_order = frappe.get_doc("Work Order", name)
			work_order.wip_warehouse = "Work In Progress - _TC"
			work_order.fg_warehouse = work_order.fg_warehouse or "Finished Goods - _TC"
			work_order.submit()
			self.assert_job_card_matches_schedule(plan, work_order)

		self.assertRaises(frappe.ValidationError, apply_schedule, plan.name, start_date)

	def assert_job_card_matches_schedule(self, plan, work_order):
		plan_row = work_order.production_plan_item or work_order.production_plan_sub_assembly_item
		entries = frappe.get_all(
			"Production Plan Schedule",
			filters={"production_plan": plan.name, "plan_row": plan_row},
			fields=["from_time", "to_time", "workstation"],
			order_by="from_time",
		)
		self.assertTrue(entries)

		job_card = frappe.get_doc("Job Card", {"work_order": work_order.name})
		self.assertEqual(len(job_card.scheduled_time_logs), len(entries))
		for log, entry in zip(job_card.scheduled_time_logs, entries, strict=True):
			self.assertEqual(get_datetime(log.from_time), get_datetime(entry.from_time))
			self.assertEqual(get_datetime(log.to_time), get_datetime(entry.to_time))

		self.assertEqual(job_card.workstation, entries[0].workstation)
		self.assertEqual(get_datetime(job_card.expected_start_date), get_datetime(entries[0].from_time))
		self.assertEqual(get_datetime(job_card.expected_end_date), get_datetime(entries[-1].to_time))

		operation_row = work_order.operations[0]
		self.assertEqual(get_datetime(operation_row.planned_start_time), get_datetime(entries[0].from_time))
		self.assertEqual(get_datetime(operation_row.planned_end_time), get_datetime(entries[-1].to_time))

	@change_settings("Manufacturing Settings", {"mins_between_operations": 10, "allow_overtime": 0})
	def test_item_wise_start_dates(self):
		day_one = get_datetime("2026-09-01 09:00:00")
		day_two = get_datetime("2026-09-02 09:00:00")

		plan = create_production_plan(
			item_code="Test PPS FG",
			planned_qty=2,
			planned_start_date=day_one,
			use_multi_level_bom=1,
			do_not_submit=True,
			skip_getting_mr_items=True,
		)
		plan.append(
			"po_items",
			{
				"use_multi_level_bom": 1,
				"item_code": "Test PPS FG 2",
				"bom_no": frappe.db.get_value("Item", "Test PPS FG 2", "default_bom"),
				"planned_qty": 2,
				"planned_start_date": day_one,
				"stock_uom": "Nos",
				"warehouse": plan.po_items[0].warehouse,
			},
		)
		plan.get_sub_assembly_items()
		plan.submit()

		apply_schedule(plan.name, day_one, use_item_dates=1, item_dates={plan.po_items[1].name: str(day_two)})
		plan.reload()

		fg_one, fg_two = plan.po_items
		self.assertEqual(get_datetime(fg_two.planned_start_date), day_two)
		self.assertEqual(get_datetime(fg_two.planned_end_date), add_to_date(day_two, minutes=60))
		# no dialog date for the first row, so its computed start (after both
		# sub-assemblies and the operation gap) is persisted to match the calendar
		self.assertEqual(get_datetime(fg_one.planned_start_date), add_to_date(day_one, minutes=250))
		self.assertEqual(get_datetime(fg_one.planned_end_date), add_to_date(day_one, minutes=310))

		for row in plan.sub_assembly_items:
			self.assertGreaterEqual(get_datetime(row.schedule_date), day_one)

	@change_settings("Manufacturing Settings", {"mins_between_operations": 10, "allow_overtime": 0})
	def test_cleared_item_date_frees_the_chain(self):
		day_one = get_datetime("2026-12-01 09:00:00")
		day_two = get_datetime("2026-12-02 09:00:00")

		plan = self.make_plan()
		fg_row = plan.po_items[0].name

		apply_schedule(plan.name, day_one, use_item_dates=1, item_dates={fg_row: str(day_two)})
		plan.reload()
		self.assertEqual(get_datetime(plan.po_items[0].planned_start_date), day_two)

		apply_schedule(plan.name, day_one, use_item_dates=1, item_dates={})
		plan.reload()

		# the cleared date no longer constrains the chain, so the item schedules
		# freely from the dialog start date instead of the stale persisted one
		self.assertEqual(get_datetime(plan.po_items[0].planned_start_date), add_to_date(day_one, minutes=250))

	@change_settings("Manufacturing Settings", {"mins_between_operations": 10, "allow_overtime": 0})
	def test_other_plan_schedule_blocks_are_treated_as_load(self):
		start_date = get_datetime("2027-01-04 09:00:00")
		plan_one = self.make_plan()
		apply_schedule(plan_one.name, start_date)

		own_preview = get_schedule_preview(plan_one.name, start_date)
		own_starts = sorted(
			row["start"] for row in own_preview["rows"].values() if row["row_type"] == "Sub Assembly"
		)
		self.assertEqual(own_starts[0], start_date)

		plan_two = self.make_plan()
		preview = get_schedule_preview(plan_two.name, start_date)
		self.assertFalse(preview["unscheduled"])
		self.assert_no_block_overlap(plan_one.name, preview)

		plan_one.reload()
		plan_one.cancel()
		preview_after_cancel = get_schedule_preview(plan_two.name, start_date)
		two_starts = sorted(
			row["start"] for row in preview_after_cancel["rows"].values() if row["row_type"] == "Sub Assembly"
		)
		self.assertEqual(two_starts[0], start_date)

	def assert_no_block_overlap(self, plan_name, preview):
		entries = frappe.get_all(
			"Production Plan Schedule",
			filters={"production_plan": plan_name},
			fields=["workstation", "from_time", "to_time"],
		)
		blocks = [
			block for row in preview["rows"].values() for block in row["blocks"] if block.get("workstation")
		]
		self.assertTrue(entries)
		self.assertTrue(blocks)

		for entry in entries:
			for block in blocks:
				overlaps = get_datetime(entry.from_time) < block["to_time"] and block[
					"from_time"
				] < get_datetime(entry.to_time)
				self.assertFalse(overlaps, f"{block['task_key']} overlaps a block of {plan_name}")

	@change_settings(
		"Manufacturing Settings",
		{"mins_between_operations": 10, "allow_overtime": 0, "disable_capacity_planning": 0},
	)
	def test_partially_submitted_plan_keeps_schedule_load(self):
		start_date = get_datetime("2027-03-01 09:00:00")
		plan_one = self.make_plan()
		apply_schedule(plan_one.name, start_date)

		plan_one.reload()
		plan_one.make_work_order()
		work_order_name = frappe.get_all(
			"Work Order",
			filters={"production_plan": plan_one.name, "production_plan_sub_assembly_item": ("is", "set")},
			pluck="name",
		)[0]

		work_order = frappe.get_doc("Work Order", work_order_name)
		work_order.wip_warehouse = "Work In Progress - _TC"
		work_order.fg_warehouse = work_order.fg_warehouse or "Finished Goods - _TC"
		work_order.submit()

		plan_two = self.make_plan()
		preview = get_schedule_preview(plan_two.name, start_date)
		self.assertFalse(preview["unscheduled"])
		self.assert_no_block_overlap(plan_one.name, preview)

	def test_schedule_entry_overlap_validation(self):
		workstation = "Test PPS WS Cap2"
		if not frappe.db.exists("Workstation", workstation):
			make_workstation(workstation=workstation, production_capacity=2)

		plan = self.make_plan()

		def make_entry(from_time, to_time):
			entry = frappe.get_doc(
				{
					"doctype": "Production Plan Schedule",
					"production_plan": plan.name,
					"row_type": "Finished Good",
					"item_code": "Test PPS FG",
					"workstation": workstation,
					"from_time": from_time,
					"to_time": to_time,
				}
			)
			entry.flags.from_scheduler = True
			return entry

		make_entry("2027-02-01 09:00:00", "2027-02-01 10:00:00").insert()
		make_entry("2027-02-01 09:30:00", "2027-02-01 10:30:00").insert()

		self.assertRaises(OverlapError, make_entry("2027-02-01 09:45:00", "2027-02-01 10:15:00").insert)
		self.assertRaises(
			frappe.ValidationError, make_entry("2027-02-01 12:00:00", "2027-02-01 11:00:00").insert
		)

		make_entry("2027-02-01 10:30:00", "2027-02-01 11:30:00").insert()

	@change_settings(
		"Manufacturing Settings",
		{"mins_between_operations": 10, "allow_overtime": 0, "disable_capacity_planning": 0},
	)
	def test_partial_job_cards_keep_remaining_schedule_load(self):
		operation_two = "Test PPS Op 2"
		if not frappe.db.exists("Operation", operation_two):
			make_operation(operation=operation_two, workstation=self.workstation)

		item = "Test PPS FG 3"
		create_item(item, valuation_rate=100)
		self.make_bom_with_operation(
			item, ["Test PPS RM"], time_in_mins=60, operations=[self.operation, operation_two]
		)

		plan = create_production_plan(
			item_code=item, planned_qty=1, do_not_submit=True, skip_getting_mr_items=True
		)
		plan.submit()

		start_date = get_datetime("2027-04-05 09:00:00")
		apply_schedule(plan.name, start_date)

		plan.reload()
		plan.make_work_order()
		work_order = frappe.get_doc("Work Order", {"production_plan": plan.name})
		work_order.wip_warehouse = "Work In Progress - _TC"
		work_order.fg_warehouse = work_order.fg_warehouse or "Finished Goods - _TC"
		work_order.submit()

		job_card = frappe.db.get_value(
			"Job Card", {"work_order": work_order.name, "operation": operation_two}
		)
		frappe.delete_doc("Job Card", job_card)

		entries = frappe.get_all(
			"Production Plan Schedule",
			filters={"production_plan": plan.name, "workstation": self.workstation},
			fields=["from_time", "to_time"],
		)
		expected = sorted((get_datetime(row.from_time), get_datetime(row.to_time)) for row in entries)
		self.assertEqual(len(expected), 2)

		booked = sorted(
			(interval.start, interval.end)
			for interval in loaders.get_booked_load([self.workstation], start_date)[self.workstation]
		)
		self.assertEqual(booked, expected)

	@change_settings(
		"Manufacturing Settings",
		{"mins_between_operations": 10, "allow_overtime": 0, "disable_capacity_planning": 1},
	)
	def test_batch_split_job_cards_keep_schedule_load(self):
		operation = "Test PPS Op Batch"
		if not frappe.db.exists("Operation", operation):
			make_operation(operation=operation, workstation=self.workstation)
		frappe.db.set_value("Operation", operation, "create_job_card_based_on_batch_size", 1)

		item = "Test PPS FG 4"
		create_item(item, valuation_rate=100)
		self.make_bom_with_operation(
			item, ["Test PPS RM"], time_in_mins=30, operations=[operation], batch_size=1
		)

		plan = create_production_plan(
			item_code=item, planned_qty=2, do_not_submit=True, skip_getting_mr_items=True
		)
		plan.submit()

		start_date = get_datetime("2027-05-03 09:00:00")
		apply_schedule(plan.name, start_date)

		plan.reload()
		plan.make_work_order()
		work_order = frappe.get_doc("Work Order", {"production_plan": plan.name})
		work_order.wip_warehouse = "Work In Progress - _TC"
		work_order.fg_warehouse = work_order.fg_warehouse or "Finished Goods - _TC"
		work_order.submit()

		job_cards = frappe.get_all("Job Card", filters={"work_order": work_order.name}, pluck="name")
		self.assertEqual(len(job_cards), 2)
		self.assertFalse(
			frappe.db.exists("Job Card Scheduled Time", {"parent": ("in", job_cards)}),
		)

		entries = frappe.get_all(
			"Production Plan Schedule",
			filters={"production_plan": plan.name, "workstation": self.workstation},
			fields=["from_time", "to_time"],
		)
		self.assertTrue(entries)

		booked = {
			(interval.start, interval.end)
			for interval in loaders.get_booked_load([self.workstation], start_date)[self.workstation]
		}
		for row in entries:
			self.assertIn((get_datetime(row.from_time), get_datetime(row.to_time)), booked)

	@change_settings(
		"Manufacturing Settings",
		{"mins_between_operations": 10, "allow_overtime": 0, "disable_capacity_planning": 0},
	)
	def test_partially_covered_batch_split_restores_schedule_load(self):
		operation = "Test PPS Op Batch"
		if not frappe.db.exists("Operation", operation):
			make_operation(operation=operation, workstation=self.workstation)
		frappe.db.set_value("Operation", operation, "create_job_card_based_on_batch_size", 1)

		item = "Test PPS FG 5"
		create_item(item, valuation_rate=100)
		self.make_bom_with_operation(
			item, ["Test PPS RM"], time_in_mins=30, operations=[operation], batch_size=1
		)

		plan = create_production_plan(
			item_code=item, planned_qty=2, do_not_submit=True, skip_getting_mr_items=True
		)
		plan.submit()

		start_date = get_datetime("2027-06-07 09:00:00")
		apply_schedule(plan.name, start_date)

		plan.reload()
		plan.make_work_order()
		work_order = frappe.get_doc("Work Order", {"production_plan": plan.name})
		work_order.wip_warehouse = "Work In Progress - _TC"
		work_order.fg_warehouse = work_order.fg_warehouse or "Finished Goods - _TC"
		work_order.submit()

		job_cards = frappe.get_all("Job Card", filters={"work_order": work_order.name}, pluck="name")
		self.assertEqual(len(job_cards), 2)
		scheduled_rows = frappe.db.count("Job Card Scheduled Time", {"parent": ("in", job_cards)})
		self.assertTrue(scheduled_rows)

		booked = loaders.get_booked_load([self.workstation], start_date)[self.workstation]
		self.assertEqual(len(booked), scheduled_rows)

		frappe.delete_doc("Job Card", job_cards[1])

		entry_count = frappe.db.count(
			"Production Plan Schedule", {"production_plan": plan.name, "workstation": self.workstation}
		)
		remaining_rows = frappe.db.count("Job Card Scheduled Time", {"parent": ("in", job_cards)})
		booked = loaders.get_booked_load([self.workstation], start_date)[self.workstation]
		self.assertEqual(len(booked), remaining_rows + entry_count)

	def test_manual_schedule_entry_creation_is_blocked(self):
		plan = self.make_plan()
		entry = frappe.get_doc(
			{
				"doctype": "Production Plan Schedule",
				"production_plan": plan.name,
				"item_code": "Test PPS FG",
				"from_time": "2026-11-02 09:00:00",
				"to_time": "2026-11-02 10:00:00",
			}
		)

		self.assertRaises(frappe.ValidationError, entry.insert)

	def test_incomplete_proposal_is_not_applied(self):
		from unittest.mock import patch

		from erpnext.manufacturing.scheduling import plan_adapter

		plan = self.make_plan()
		incomplete = {
			"rows": {},
			"unscheduled": {"task": "no capacity within horizon"},
			"completion_date": None,
		}

		with patch.object(plan_adapter, "run_engine", return_value=incomplete):
			self.assertRaises(frappe.ValidationError, apply_schedule, plan.name, "2026-11-02 09:00:00")

	@change_settings("Manufacturing Settings", {"mins_between_operations": 10, "allow_overtime": 0})
	def test_schedule_considers_raw_material_lead_time(self):
		if frappe.db.exists("Item Lead Time", "Test PPS RM"):
			frappe.db.set_value("Item Lead Time", "Test PPS RM", {"purchase_time": 2, "buffer_time": 0})
		else:
			frappe.get_doc(
				{"doctype": "Item Lead Time", "item_code": "Test PPS RM", "purchase_time": 2}
			).insert()
		self.addCleanup(frappe.delete_doc, "Item Lead Time", "Test PPS RM", force=True)

		plan = self.make_plan()
		start_date = get_datetime("2026-11-02 09:00:00")
		preview = get_schedule_preview(plan.name, start_date)

		material_row = preview["rows"].get("material:Test PPS RM")
		self.assertIsNotNone(material_row)
		self.assertEqual(material_row["start"], start_date)
		self.assertEqual(material_row["end"], add_to_date(start_date, days=2))

		material_arrival = add_to_date(start_date, days=2, minutes=10)
		sub_starts = sorted(
			row["start"] for row in preview["rows"].values() if row["row_type"] == "Sub Assembly"
		)
		self.assertEqual(sub_starts, [material_arrival, add_to_date(material_arrival, minutes=120)])

	@change_settings("Manufacturing Settings", {"mins_between_operations": 10, "allow_overtime": 0})
	def test_preview_and_apply_schedule(self):
		plan = self.make_plan()
		start_date = get_datetime("2026-08-13 09:00:00")

		preview = get_schedule_preview(plan.name, start_date)
		self.assertEqual(len(preview["rows"]), 3)
		self.assertFalse(preview["unscheduled"])

		sub_starts = sorted(
			row["start"] for row in preview["rows"].values() if row["row_type"] == "Sub Assembly"
		)
		self.assertEqual(sub_starts, [start_date, add_to_date(start_date, minutes=120)])

		fg_row = next(row for row in preview["rows"].values() if row["row_type"] == "Finished Good")
		self.assertEqual(fg_row["start"], add_to_date(start_date, minutes=250))
		self.assertEqual(preview["completion_date"], add_to_date(start_date, minutes=310))

		self.assertFalse(frappe.db.exists("Production Plan Schedule", {"production_plan": plan.name}))

		apply_schedule(plan.name, start_date)

		entries = frappe.get_all(
			"Production Plan Schedule",
			filters={"production_plan": plan.name},
			fields=["workstation", "from_time", "to_time", "row_type", "operation"],
		)
		self.assertEqual(len(entries), 3)
		self.assertTrue(all(entry.workstation == self.workstation for entry in entries))

		plan.reload()
		self.assertEqual(get_datetime(plan.po_items[0].planned_start_date), fg_row["start"])
		self.assertEqual(get_datetime(plan.po_items[0].planned_end_date), preview["completion_date"])
		for row in plan.sub_assembly_items:
			self.assertIn(get_datetime(row.schedule_date), sub_starts)
			self.assertIsNotNone(row.schedule_end_date)
