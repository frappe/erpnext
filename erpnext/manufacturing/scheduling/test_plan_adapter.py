# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import change_settings
from frappe.utils import add_to_date, get_datetime

from erpnext.manufacturing.doctype.production_plan.test_production_plan import (
	create_production_plan,
	make_bom,
)
from erpnext.manufacturing.doctype.work_order.test_work_order import make_operation, make_workstation
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

	def make_bom_with_operation(self, item, raw_materials, time_in_mins):
		if frappe.db.exists("BOM", {"item": item, "docstatus": 1}):
			return

		bom = make_bom(item=item, raw_materials=raw_materials, with_operations=1, do_not_save=True)
		bom.append(
			"operations",
			{
				"operation": self.operation,
				"workstation": self.workstation,
				"time_in_mins": time_in_mins,
				"hour_rate": 100,
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

		apply_schedule(
			plan.name, day_one, use_item_dates=1, item_dates={plan.po_items[1].name: str(day_two)}
		)
		plan.reload()

		fg_one, fg_two = plan.po_items
		self.assertEqual(get_datetime(fg_two.planned_start_date), day_two)
		self.assertEqual(get_datetime(fg_two.planned_end_date), add_to_date(day_two, minutes=60))
		self.assertEqual(get_datetime(fg_one.planned_start_date), day_one)
		self.assertEqual(get_datetime(fg_one.planned_end_date), add_to_date(day_one, minutes=310))

		for row in plan.sub_assembly_items:
			self.assertGreaterEqual(get_datetime(row.schedule_date), day_one)

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
			self.assertRaises(
				frappe.ValidationError, apply_schedule, plan.name, "2026-11-02 09:00:00"
			)

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
