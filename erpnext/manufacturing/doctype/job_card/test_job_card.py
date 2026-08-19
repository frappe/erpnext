# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


from typing import Literal

import frappe
from frappe.utils import flt, random_string
from frappe.utils.data import add_to_date, now, today

from erpnext.manufacturing.doctype.job_card.job_card import (
	JobCardOverTransferError,
	OperationSequenceError,
	OverlapError,
)
from erpnext.manufacturing.doctype.job_card.mapper import (
	make_corrective_job_card,
	make_material_request,
)
from erpnext.manufacturing.doctype.job_card.mapper import (
	make_stock_entry as make_stock_entry_from_jc,
)
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.doctype.work_order.work_order import WorkOrder, make_work_order
from erpnext.manufacturing.doctype.workstation.test_workstation import make_workstation
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.tests.utils import ERPNextTestSuite


class TestJobCard(ERPNextTestSuite):
	def setUp(self):
		self.load_test_records("BOM")
		self.make_bom_for_jc_tests()
		self.transfer_material_against: Literal["Work Order", "Job Card"] = "Work Order"
		self.source_warehouse = None
		self._work_order = None

	def make_bom_for_jc_tests(self):
		bom = frappe.copy_doc(self.globalTestRecords["BOM"][2])
		bom.set_rate_of_sub_assembly_item_based_on_bom = 0
		bom.rm_cost_as_per = "Valuation Rate"
		bom.items[0].uom = "_Test UOM 1"
		bom.items[0].conversion_factor = 5
		bom.insert()

	@property
	def work_order(self) -> WorkOrder:
		"""Work Order lazily created for tests."""
		if not self._work_order:
			self._work_order = make_wo_order_test_record(
				item="_Test FG Item 2",
				qty=2,
				transfer_material_against=self.transfer_material_against,
				source_warehouse=self.source_warehouse,
			)
		return self._work_order

	def generate_required_stock(self, work_order: WorkOrder) -> None:
		"""Create twice the stock for all required items in work order."""
		for item in work_order.required_items:
			make_stock_entry(
				item_code=item.item_code,
				target=item.source_warehouse or self.source_warehouse,
				qty=item.required_qty * 2,
				basic_rate=100,
			)

	def test_quality_inspection_mandatory_check(self):
		from erpnext.manufacturing.doctype.operation.test_operation import make_operation

		raw = create_item("Fabric-Raw")
		cut_fg = create_item("Cut-Fabric-SFG")
		stitch_fg = create_item("Stitched-TShirt-SFG")
		final = create_item("Finished-TShirt")

		row = {"operation": "Cutting", "workstation": "_Test Workstation 1"}

		cutting = make_operation(row)
		stitching = make_operation({"operation": "Stitching", "workstation": "_Test Workstation 1"})
		ironing = make_operation({"operation": "Ironing", "workstation": "_Test Workstation 1"})

		cut_bom = create_semi_fg_bom(cut_fg.name, raw.name, inspection_required=1)
		stitch_bom = create_semi_fg_bom(stitch_fg.name, cut_fg.name, inspection_required=0)
		final_bom = frappe.new_doc(
			"BOM",
			item=final.name,
			quantity=1,
			with_operations=1,
			track_semi_finished_goods=1,
			company="_Test Company",
			inspection_required=1,
		)
		final_bom.append("items", {"item_code": raw.name, "qty": 1})
		final_bom.append(
			"operations",
			{
				"operation": cutting.name,
				"workstation": "_Test Workstation 1",
				"bom_no": cut_bom,
				"skip_material_transfer": 1,
				"time_in_mins": 60,
				"quality_inspection_required": 1,
			},
		)
		final_bom.append(
			"operations",
			{
				"operation": stitching.name,
				"workstation": "_Test Workstation 1",
				"bom_no": stitch_bom,
				"skip_material_transfer": 1,
				"time_in_mins": 60,
			},
		)
		final_bom.append(
			"operations",
			{
				"operation": ironing.name,
				"workstation": "_Test Workstation 1",
				"bom_no": final_bom.name,
				"is_final_finished_good": 1,
				"skip_material_transfer": 1,
				"time_in_mins": 60,
			},
		)
		final_bom.append("items", {"item_code": stitch_fg.name, "qty": 1, "operation_row_id": 3})
		final_bom.insert()
		final_bom.submit()
		work_order = make_work_order(final_bom.name, final.name, 1, variant_items=[], use_multi_level_bom=0)
		work_order.company = "_Test Company"
		work_order.wip_warehouse = "Work In Progress - _TC"
		work_order.fg_warehouse = "Finished Goods - _TC"
		work_order.scrap_warehouse = "All Warehouses - _TC"
		for operation in work_order.operations:
			operation.time_in_mins = 60

		work_order.submit()
		job_card = frappe.get_all("Job Card", filters={"work_order": work_order.name, "operation": "Cutting"})
		job_card_doc = frappe.get_doc("Job Card", job_card[0].name)
		job_card_doc.append(
			"time_logs",
			{
				"from_time": "2024-01-01 08:00:00",
				"to_time": "2024-01-01 09:00:00",
				"time_in_mins": 60,
				"completed_qty": 1,
			},
		)
		self.assertRaises(frappe.ValidationError, job_card_doc.submit)

	def test_set_operation_id(self):
		work_order = make_wo_order_test_record(item="_Test FG Item 2", qty=2, do_not_submit=1)
		operation_row = work_order.operations[0]

		job_card = frappe.new_doc("Job Card")
		job_card.work_order = work_order.name
		job_card.operation = operation_row.operation
		job_card.set_operation_id()
		self.assertEqual(job_card.operation_id, operation_row.name)

		work_order.append(
			"operations",
			{
				"operation": operation_row.operation,
				"workstation": operation_row.workstation,
				"time_in_mins": operation_row.time_in_mins,
				"hour_rate": operation_row.hour_rate,
				"sequence_id": work_order.operations[-1].sequence_id,
			},
		)
		work_order.save()

		job_card = frappe.new_doc("Job Card")
		job_card.work_order = work_order.name
		job_card.operation = operation_row.operation
		self.assertRaises(frappe.ValidationError, job_card.set_operation_id)

		job_card.operation_id = "bogus-row"
		self.assertRaises(frappe.ValidationError, job_card.set_operation_id)

		job_card.operation_id = work_order.operations[-1].name
		job_card.set_operation_id()
		self.assertEqual(job_card.operation_id, work_order.operations[-1].name)

	def test_job_card_with_different_work_station(self):
		job_cards = frappe.get_all(
			"Job Card",
			filters={"work_order": self.work_order.name},
			fields=["operation_id", "workstation", "name", "for_quantity"],
		)

		job_card = job_cards[0]

		if job_card:
			workstation = frappe.db.get_value(
				"Workstation", {"name": ("not in", [job_card.workstation])}, "name"
			)

			if not workstation or job_card.workstation == workstation:
				workstation = make_workstation(workstation_name=random_string(5)).name

			doc = frappe.get_doc("Job Card", job_card.name)
			doc.workstation = workstation
			doc.append(
				"time_logs",
				{
					"from_time": "2009-01-01 12:06:25",
					"to_time": "2009-01-01 12:37:25",
					"time_in_mins": "31.00002",
					"completed_qty": job_card.for_quantity,
				},
			)
			doc.submit()

			completed_qty = frappe.db.get_value(
				"Work Order Operation", job_card.operation_id, "completed_qty"
			)
			self.assertEqual(completed_qty, job_card.for_quantity)

	def test_job_card_cannot_be_submitted_while_on_hold(self):
		# Regression for #55756: a paused (On Hold) job card must not be submittable, otherwise
		# the document gets locked in the On Hold state with Resume/Complete no longer available.
		job_card = frappe.get_all(
			"Job Card",
			filters={"work_order": self.work_order.name},
			fields=["name", "for_quantity"],
		)[0]

		doc = frappe.get_doc("Job Card", job_card.name)
		doc.append(
			"time_logs",
			{
				"from_time": "2024-01-01 08:00:00",
				"to_time": "2024-01-01 09:00:00",
				"time_in_mins": 60,
				"completed_qty": job_card.for_quantity,
			},
		)
		doc.is_paused = 1
		self.assertRaises(frappe.ValidationError, doc.submit)

	def test_job_card_overlap(self):
		wo2 = make_wo_order_test_record(item="_Test FG Item 2", qty=2)

		jc1 = frappe.get_last_doc("Job Card", {"work_order": self.work_order.name})
		jc2 = frappe.get_last_doc("Job Card", {"work_order": wo2.name})

		employee = frappe.db.get_all("Employee", {"first_name": "_Test Employee"})[0].name

		jc1.append(
			"time_logs",
			{
				"from_time": "2021-01-01 00:00:00",
				"to_time": "2021-01-01 08:00:00",
				"completed_qty": 1,
				"employee": employee,
			},
		)
		jc1.save()

		# add a new entry in same time slice
		jc2.append(
			"time_logs",
			{
				"from_time": "2021-01-01 00:01:00",
				"to_time": "2021-01-01 06:00:00",
				"completed_qty": 1,
				"employee": employee,
			},
		)
		self.assertRaises(OverlapError, jc2.save)

	def test_job_card_overlap_with_capacity(self):
		wo2 = make_wo_order_test_record(item="_Test FG Item 2", qty=2)

		workstation = make_workstation(workstation_name=random_string(5)).name
		frappe.db.set_value("Workstation", workstation, "production_capacity", 1)

		jc1 = frappe.get_last_doc("Job Card", {"work_order": self.work_order.name})
		jc2 = frappe.get_last_doc("Job Card", {"work_order": wo2.name})

		jc1.workstation = workstation
		jc1.append(
			"time_logs",
			{"from_time": "2021-01-01 00:00:00", "to_time": "2021-01-01 08:00:00", "completed_qty": 1},
		)
		jc1.save()

		jc2.workstation = workstation

		# add a new entry in same time slice
		jc2.append(
			"time_logs",
			{"from_time": "2021-01-01 00:01:00", "to_time": "2021-01-01 06:00:00", "completed_qty": 1},
		)
		self.assertRaises(OverlapError, jc2.save)

		frappe.db.set_value("Workstation", workstation, "production_capacity", 2)
		jc2.load_from_db()

		jc2.workstation = workstation

		# add a new entry in same time slice
		jc2.append(
			"time_logs",
			{"from_time": "2021-01-01 00:01:00", "to_time": "2021-01-01 06:00:00", "completed_qty": 1},
		)

		jc2.save()
		self.assertTrue(jc2.name)

	def test_job_card_multiple_materials_transfer(self):
		"Test transferring RMs separately against Job Card with multiple RMs."
		self.transfer_material_against = "Job Card"
		self.source_warehouse = "Stores - _TC"

		self.generate_required_stock(self.work_order)

		job_card_name = frappe.db.get_value("Job Card", {"work_order": self.work_order.name})
		job_card = frappe.get_doc("Job Card", job_card_name)

		transfer_entry_1 = make_stock_entry_from_jc(job_card_name)
		del transfer_entry_1.items[1]  # transfer only 1 of 2 RMs
		transfer_entry_1.insert()
		transfer_entry_1.submit()

		job_card.reload()

		self.assertEqual(transfer_entry_1.fg_completed_qty, 2)
		self.assertEqual(job_card.transferred_qty, 2)

		# transfer second RM
		transfer_entry_2 = make_stock_entry_from_jc(job_card_name)
		del transfer_entry_2.items[0]
		transfer_entry_2.insert()
		transfer_entry_2.submit()

		# 'For Quantity' here will be 0 since
		# transfer was made for 2 fg qty in first transfer Stock Entry
		self.assertEqual(transfer_entry_2.fg_completed_qty, 0)

	@ERPNextTestSuite.change_settings("Manufacturing Settings", {"job_card_excess_transfer": 1})
	def test_job_card_excess_material_transfer(self):
		"Test transferring more than required RM against Job Card."
		self.transfer_material_against = "Job Card"
		self.source_warehouse = "Stores - _TC"

		self.generate_required_stock(self.work_order)

		job_card = frappe.get_last_doc("Job Card", {"work_order": self.work_order.name})
		self.assertEqual(job_card.status, "Open")

		# fully transfer both RMs
		transfer_entry_1 = make_stock_entry_from_jc(job_card.name)
		transfer_entry_1.insert()
		transfer_entry_1.submit()

		# transfer extra qty of both RM due to previously damaged RM
		transfer_entry_2 = make_stock_entry_from_jc(job_card.name)
		# deliberately change 'For Quantity'
		transfer_entry_2.fg_completed_qty = 1
		transfer_entry_2.items[0].qty = 5
		transfer_entry_2.items[1].qty = 3
		transfer_entry_2.insert()
		transfer_entry_2.submit()

		job_card.reload()
		self.assertGreater(job_card.transferred_qty, job_card.for_quantity)

		# Check if 'For Quantity' is negative
		# as 'transferred_qty' > Qty to Manufacture
		transfer_entry_3 = make_stock_entry_from_jc(job_card.name)
		self.assertEqual(transfer_entry_3.fg_completed_qty, 0)

		job_card.append(
			"time_logs",
			{"from_time": "2021-01-01 00:01:00", "to_time": "2021-01-01 06:00:00", "completed_qty": 2},
		)
		job_card.save()
		job_card.submit()

		# JC is Completed with excess transfer
		self.assertEqual(job_card.status, "Completed")

	def test_job_card_actions_blocked_until_material_transfer(self):
		"Start and Complete must wait for the transfer when RMs move against Job Card."
		self.transfer_material_against = "Job Card"
		self.source_warehouse = "Stores - _TC"

		self.generate_required_stock(self.work_order)
		job_card = frappe.get_last_doc("Job Card", {"work_order": self.work_order.name})

		self.assertRaises(frappe.ValidationError, job_card.start_timer, start_time=now())
		self.assertRaises(frappe.ValidationError, job_card.complete_job_card, qty=2, for_quantity=2)

		transfer_entry = make_stock_entry_from_jc(job_card.name)
		transfer_entry.insert()
		transfer_entry.submit()

		job_card.reload()
		job_card.append("time_logs", {"from_time": "2024-03-01 08:00:00"})
		job_card.save()
		job_card.complete_job_card(
			qty=2, for_quantity=2, pending_qty=0, process_loss_qty=0, end_time="2024-03-01 09:00:00"
		)

		job_card.reload()
		self.assertEqual(flt(job_card.total_completed_qty), 2)

	@ERPNextTestSuite.change_settings("Manufacturing Settings", {"job_card_excess_transfer": 0})
	def test_job_card_excess_material_transfer_block(self):
		self.transfer_material_against = "Job Card"
		self.source_warehouse = "Stores - _TC"

		self.generate_required_stock(self.work_order)

		job_card_name = frappe.db.get_value("Job Card", {"work_order": self.work_order.name})

		# fully transfer both RMs
		transfer_entry_1 = make_stock_entry_from_jc(job_card_name)
		transfer_entry_1.insert()
		transfer_entry_1.submit()

		# transfer extra qty of both RM due to previously damaged RM
		transfer_entry_2 = make_stock_entry_from_jc(job_card_name)
		# deliberately change 'For Quantity'
		transfer_entry_2.fg_completed_qty = 1
		transfer_entry_2.items[0].qty = 5
		transfer_entry_2.items[1].qty = 3
		transfer_entry_2.insert()
		self.assertRaises(JobCardOverTransferError, transfer_entry_2.submit)

	@ERPNextTestSuite.change_settings("Manufacturing Settings", {"job_card_excess_transfer": 0})
	def test_job_card_excess_material_transfer_with_no_reference(self):
		self.transfer_material_against = "Job Card"
		self.source_warehouse = "Stores - _TC"

		self.generate_required_stock(self.work_order)

		job_card_name = frappe.db.get_value("Job Card", {"work_order": self.work_order.name})

		# fully transfer both RMs
		transfer_entry_1 = make_stock_entry_from_jc(job_card_name)
		row = transfer_entry_1.items[0]

		# Add new row without reference of the job card item
		transfer_entry_1.append(
			"items",
			{
				"item_code": row.item_code,
				"item_name": row.item_name,
				"item_group": row.item_group,
				"qty": row.qty,
				"uom": row.uom,
				"conversion_factor": row.conversion_factor,
				"stock_uom": row.stock_uom,
				"basic_rate": row.basic_rate,
				"basic_amount": row.basic_amount,
				"expense_account": row.expense_account,
				"cost_center": row.cost_center,
				"s_warehouse": row.s_warehouse,
				"t_warehouse": row.t_warehouse,
			},
		)

		self.assertRaises(frappe.ValidationError, transfer_entry_1.insert)

	def test_job_card_partial_material_transfer(self):
		"Test partial material transfer against Job Card"
		self.transfer_material_against = "Job Card"
		self.source_warehouse = "Stores - _TC"

		self.generate_required_stock(self.work_order)

		job_card = frappe.get_last_doc("Job Card", {"work_order": self.work_order.name})

		# partially transfer
		transfer_entry = make_stock_entry_from_jc(job_card.name)
		transfer_entry.fg_completed_qty = 1
		transfer_entry.get_items()
		transfer_entry.insert()
		transfer_entry.submit()

		job_card.reload()
		self.assertEqual(job_card.transferred_qty, 1)
		self.assertEqual(transfer_entry.items[0].qty, 5)
		self.assertEqual(transfer_entry.items[1].qty, 3)

		# transfer remaining
		transfer_entry_2 = make_stock_entry_from_jc(job_card.name)

		self.assertEqual(transfer_entry_2.fg_completed_qty, 1)
		self.assertEqual(transfer_entry_2.items[0].qty, 5)
		self.assertEqual(transfer_entry_2.items[1].qty, 3)

		transfer_entry_2.insert()
		transfer_entry_2.submit()

		job_card.reload()
		self.assertEqual(job_card.transferred_qty, 2)

		transfer_entry_2.cancel()
		transfer_entry.cancel()

		job_card.reload()
		self.assertEqual(job_card.transferred_qty, 0.0)

	def test_job_card_material_transfer_correctness(self):
		"""
		1. Test if only current Job Card Items are pulled in a Stock Entry against a Job Card
		2. Test impact of changing 'For Qty' in such a Stock Entry
		"""
		create_bom_with_multiple_operations()
		work_order = make_wo_with_transfer_against_jc()

		job_card_name = frappe.db.get_value(
			"Job Card", {"work_order": work_order.name, "operation": "Test Operation A"}
		)
		job_card = frappe.get_doc("Job Card", job_card_name)

		self.assertEqual(len(job_card.items), 1)
		self.assertEqual(job_card.items[0].item_code, "_Test Item")

		# check if right items are mapped in transfer entry
		transfer_entry = make_stock_entry_from_jc(job_card_name)
		transfer_entry.insert()

		self.assertEqual(len(transfer_entry.items), 1)
		self.assertEqual(transfer_entry.items[0].item_code, "_Test Item")
		self.assertEqual(transfer_entry.items[0].qty, 4)

		# change 'For Qty' and check impact on items table
		# no.of items should be the same with qty change
		transfer_entry.fg_completed_qty = 2
		transfer_entry.get_items()

		self.assertEqual(len(transfer_entry.items), 1)
		self.assertEqual(transfer_entry.items[0].item_code, "_Test Item")
		self.assertEqual(transfer_entry.items[0].qty, 2)

	def test_work_order_transferred_qty_with_multiple_job_cards(self):
		create_bom_with_multiple_operations()
		work_order = make_wo_with_transfer_against_jc()
		self.generate_required_stock(work_order)

		job_cards = frappe.get_all(
			"Job Card",
			filters={"work_order": work_order.name},
			pluck="name",
			order_by="sequence_id",
		)
		completed_qty = (4, 3)

		for job_card_name, qty in zip(job_cards, completed_qty, strict=True):
			job_card = frappe.get_doc("Job Card", job_card_name)
			job_card.for_quantity = qty
			job_card.save()

			transfer_entry = make_stock_entry_from_jc(job_card.name)
			transfer_entry.fg_completed_qty = qty
			transfer_entry.get_items()
			transfer_entry.submit()

			job_card.reload()
			job_card.append(
				"time_logs",
				{
					"from_time": now(),
					"to_time": add_to_date(now(), hours=1),
					"completed_qty": qty,
				},
			)
			job_card.submit()

		work_order.reload()
		self.assertEqual(work_order.material_transferred_for_manufacturing, min(completed_qty))

		# Refreshing required items must not replace the Job Card roll-up with the sum
		# of FG quantities from Material Transfer Stock Entries (4 + 3).
		work_order.update_required_items()
		work_order.reload()
		self.assertEqual(work_order.material_transferred_for_manufacturing, min(completed_qty))

	def test_corrective_job_card_requires_operation_details(self):
		job_card = frappe.get_last_doc("Job Card", {"work_order": self.work_order.name})

		with self.assertRaisesRegex(frappe.ValidationError, "Corrective Operation is required"):
			make_corrective_job_card(job_card.name, for_operation=job_card.operation)

		with self.assertRaisesRegex(frappe.ValidationError, "For Operation is required"):
			make_corrective_job_card(job_card.name, operation=job_card.operation)

	def test_corrective_job_card_not_allowed_for_tracked_semi_finished_goods(self):
		job_card = frappe.get_last_doc("Job Card", {"work_order": self.work_order.name})
		job_card.db_set("track_semi_finished_goods", 1)

		with self.assertRaisesRegex(frappe.ValidationError, "track semi-finished goods"):
			make_corrective_job_card(
				job_card.name,
				operation=job_card.operation,
				for_operation=job_card.operation,
			)

	def test_corrective_job_card_does_not_copy_total_completed_qty(self):
		job_card = frappe.get_last_doc("Job Card", {"work_order": self.work_order.name})
		job_card.append(
			"time_logs",
			{"from_time": now(), "to_time": add_to_date(now(), hours=1), "completed_qty": 1},
		)
		job_card.save()
		self.assertEqual(job_card.total_completed_qty, 1)

		corrective_job_card = make_corrective_job_card(
			job_card.name,
			operation=job_card.operation,
			for_operation=job_card.operation,
		)

		self.assertEqual(corrective_job_card.total_completed_qty, 0)

	@ERPNextTestSuite.change_settings(
		"Manufacturing Settings", {"backflush_raw_materials_based_on": "Material Transferred for Manufacture"}
	)
	def test_corrective_job_card_does_not_autofill_items(self):
		self.transfer_material_against = "Job Card"
		job_card = frappe.get_last_doc("Job Card", {"work_order": self.work_order.name})
		frappe.db.set_value("BOM", job_card.bom_no, "backflush_based_on", "")
		self.assertTrue(job_card.items)

		corrective_job_card = make_corrective_job_card(
			job_card.name,
			operation=job_card.operation,
			for_operation=job_card.operation,
		)

		self.assertFalse(corrective_job_card.items)
		corrective_job_card.get_required_items()
		self.assertFalse(corrective_job_card.items)
		self.assertEqual(
			corrective_job_card.get_onload("backflush_raw_materials_based_on"),
			"Material Transferred for Manufacture",
		)

	@ERPNextTestSuite.change_settings("Manufacturing Settings", {"backflush_raw_materials_based_on": "BOM"})
	def test_corrective_job_card_uses_bom_backflush_setting(self):
		job_card = frappe.get_last_doc("Job Card", {"work_order": self.work_order.name})
		frappe.db.set_value(
			"BOM",
			job_card.bom_no,
			"backflush_based_on",
			"Material Transferred for Manufacture",
		)

		corrective_job_card = make_corrective_job_card(
			job_card.name,
			operation=job_card.operation,
			for_operation=job_card.operation,
		)

		self.assertEqual(
			corrective_job_card.get_onload("backflush_raw_materials_based_on"),
			"Material Transferred for Manufacture",
		)

	@ERPNextTestSuite.change_settings("Manufacturing Settings", {"backflush_raw_materials_based_on": "BOM"})
	def test_corrective_job_card_uses_work_order_transfer_setting(self):
		self.transfer_material_against = "Job Card"
		job_card = frappe.get_last_doc("Job Card", {"work_order": self.work_order.name})
		frappe.db.set_value("BOM", job_card.bom_no, "backflush_based_on", "BOM")

		corrective_job_card = make_corrective_job_card(
			job_card.name,
			operation=job_card.operation,
			for_operation=job_card.operation,
		)

		self.assertEqual(corrective_job_card.get_onload("backflush_raw_materials_based_on"), "BOM")
		self.assertEqual(corrective_job_card.get_onload("transfer_material_against"), "Job Card")

	def test_corrective_job_card_transfer_excluded_from_item_transferred_qty(self):
		from erpnext.manufacturing.doctype.work_order.mapper import (
			make_stock_entry as make_stock_entry_for_wo,
		)
		from erpnext.manufacturing.doctype.work_order.mapper import (
			make_stock_return_entry,
		)

		wo = make_wo_order_test_record(
			item="_Test FG Item 2",
			qty=4,
			transfer_material_against="Work Order",
			source_warehouse=self.source_warehouse,
		)
		self.generate_required_stock(wo)

		transfer = frappe.get_doc(
			make_stock_entry_for_wo(wo.name, "Material Transfer for Manufacture", qty=2)
		)
		transfer.fg_completed_qty = 0
		transfer.submit()

		job_card = frappe.get_last_doc("Job Card", {"work_order": wo.name})
		job_card.append(
			"time_logs",
			{"from_time": now(), "to_time": add_to_date(now(), hours=1), "completed_qty": 4},
		)
		job_card.submit()

		corrective_operation = frappe.get_doc(
			doctype="Operation", is_corrective_operation=1, name=frappe.generate_hash()
		).insert()
		corrective_job_card = make_corrective_job_card(
			job_card.name, operation=corrective_operation.name, for_operation=job_card.operation
		)
		corrective_job_card.for_quantity = 1
		corrective_item = create_item(f"Corrective Item {frappe.generate_hash(length=8)}")
		corrective_source_warehouse = wo.required_items[0].source_warehouse
		make_stock_entry(
			item_code=corrective_item.name,
			target=corrective_source_warehouse,
			qty=1,
			basic_rate=100,
		)
		for row in wo.required_items:
			corrective_job_card.append(
				"items",
				{
					"item_code": row.item_code,
					"source_warehouse": row.source_warehouse,
					"uom": frappe.db.get_value("Item", row.item_code, "stock_uom"),
					"required_qty": flt(row.required_qty) / 4,
				},
			)
		corrective_job_card.append(
			"items",
			{
				"item_code": corrective_item.name,
				"source_warehouse": corrective_source_warehouse,
				"uom": corrective_item.stock_uom,
				"required_qty": 1,
			},
		)
		corrective_job_card.insert()

		corrective_transfer = make_stock_entry_from_jc(corrective_job_card.name)
		corrective_transfer.submit()

		wo.reload()
		self.assertNotIn(corrective_item.name, [row.item_code for row in wo.required_items])
		for row in wo.required_items:
			self.assertEqual(flt(row.transferred_qty), flt(row.required_qty) / 2)

		stock_return = make_stock_return_entry(wo.name)
		stock_return.company = wo.company
		returned_by_item = {
			row.item_code: flt(row.transfer_qty) for row in stock_return.items if row.item_code
		}
		self.assertEqual(returned_by_item[corrective_item.name], 1)
		for row in wo.required_items:
			self.assertGreater(returned_by_item[row.item_code], flt(row.transferred_qty))

		stock_return.submit()
		wo.reload()
		for row in wo.required_items:
			self.assertEqual(flt(row.returned_qty), flt(row.transferred_qty))

	@ERPNextTestSuite.change_settings(
		"Manufacturing Settings",
		{
			"backflush_raw_materials_based_on": "Material Transferred for Manufacture",
			"overproduction_percentage_for_work_order": 0,
		},
	)
	def test_corrective_job_card_transfer_excluded_from_transferred_qty(self):
		from erpnext.manufacturing.doctype.work_order.mapper import (
			make_stock_entry as make_stock_entry_for_wo,
		)

		wo = make_wo_order_test_record(
			item="_Test FG Item 2",
			qty=4,
			transfer_material_against="Work Order",
			source_warehouse=self.source_warehouse,
		)
		self.generate_required_stock(wo)

		transfer = frappe.get_doc(
			make_stock_entry_for_wo(wo.name, "Material Transfer for Manufacture", qty=4)
		)
		transfer.submit()

		job_card = frappe.get_last_doc("Job Card", {"work_order": wo.name})
		job_card.append(
			"time_logs",
			{"from_time": now(), "to_time": add_to_date(now(), hours=1), "completed_qty": 4},
		)
		job_card.submit()

		corrective_operation = frappe.get_doc(
			doctype="Operation", is_corrective_operation=1, name=frappe.generate_hash()
		).insert()
		corrective_job_card = make_corrective_job_card(
			job_card.name, operation=corrective_operation.name, for_operation=job_card.operation
		)
		corrective_job_card.for_quantity = 2
		rm_item = wo.required_items[0]
		corrective_job_card.append(
			"items",
			{
				"item_code": rm_item.item_code,
				"source_warehouse": rm_item.source_warehouse,
				"uom": frappe.db.get_value("Item", rm_item.item_code, "stock_uom"),
				"required_qty": 2,
			},
		)
		corrective_job_card.insert()

		corrective_transfer = make_stock_entry_from_jc(corrective_job_card.name)
		corrective_transfer.submit()

		wo.reload()
		self.assertEqual(wo.material_transferred_for_manufacturing, 4)

		original_qty = sum(row.qty for row in transfer.items if row.item_code == rm_item.item_code)
		manufacture = frappe.get_doc(make_stock_entry_for_wo(wo.name, "Manufacture", qty=4))
		consumed = sum(
			row.qty
			for row in manufacture.items
			if row.item_code == rm_item.item_code and row.s_warehouse and not row.is_finished_item
		)
		self.assertEqual(flt(consumed), flt(original_qty + 2))

	@ERPNextTestSuite.change_settings(
		"Manufacturing Settings", {"add_corrective_operation_cost_in_finished_good_valuation": 1}
	)
	def test_corrective_costing(self):
		job_card = frappe.get_last_doc("Job Card", {"work_order": self.work_order.name})

		job_card.append(
			"time_logs",
			{"from_time": now(), "to_time": add_to_date(now(), hours=1), "completed_qty": 2},
		)
		job_card.submit()

		self.work_order.reload()
		original_cost = self.work_order.total_operating_cost

		# Create a corrective operation against it
		corrective_action = frappe.get_doc(
			doctype="Operation", is_corrective_operation=1, name=frappe.generate_hash()
		).insert()

		corrective_job_card = make_corrective_job_card(
			job_card.name, operation=corrective_action.name, for_operation=job_card.operation
		)
		corrective_job_card.hour_rate = 100
		corrective_job_card.insert()
		corrective_job_card.append(
			"time_logs",
			{
				"from_time": add_to_date(now(), hours=2),
				"to_time": add_to_date(now(), hours=2, minutes=30),
				"completed_qty": 2,
			},
		)
		corrective_job_card.submit()

		self.work_order.reload()
		cost_after_correction = self.work_order.total_operating_cost
		self.assertGreater(cost_after_correction, original_cost)

		corrective_job_card.cancel()
		self.work_order.reload()
		cost_after_cancel = self.work_order.total_operating_cost
		self.assertEqual(cost_after_cancel, original_cost)

	@ERPNextTestSuite.change_settings(
		"Manufacturing Settings", {"add_corrective_operation_cost_in_finished_good_valuation": 1}
	)
	def test_if_corrective_jc_ops_cost_is_added_to_manufacture_stock_entry(self):
		wo = make_wo_order_test_record(
			item="_Test FG Item 2",
			qty=10,
			transfer_material_against=self.transfer_material_against,
			source_warehouse=self.source_warehouse,
		)
		self.generate_required_stock(wo)
		job_card = frappe.get_last_doc("Job Card", {"work_order": wo.name})
		job_card.update({"for_quantity": 4})
		job_card.append(
			"time_logs",
			{"from_time": now(), "to_time": add_to_date(now(), hours=1), "completed_qty": 4},
		)
		job_card.submit()

		corrective_action = frappe.get_doc(
			doctype="Operation", is_corrective_operation=1, name=frappe.generate_hash()
		).insert()

		corrective_job_card = make_corrective_job_card(
			job_card.name, operation=corrective_action.name, for_operation=job_card.operation
		)
		corrective_job_card.hour_rate = 100
		corrective_job_card.insert()
		corrective_job_card.append(
			"time_logs",
			{
				"from_time": add_to_date(now(), hours=2),
				"to_time": add_to_date(now(), hours=2, minutes=30),
				"completed_qty": 4,
			},
		)
		corrective_job_card.submit()
		wo.reload()

		from erpnext.manufacturing.doctype.work_order.mapper import (
			make_stock_entry as make_stock_entry_for_wo,
		)

		stock_entry = make_stock_entry_for_wo(wo.name, "Manufacture", qty=3)
		self.assertEqual(stock_entry.additional_costs[1].amount, 37.5)
		frappe.get_doc(stock_entry).submit()

		from erpnext.manufacturing.doctype.work_order.work_order import make_job_card

		make_job_card(
			wo.name,
			[{"name": wo.operations[0].name, "operation": "_Test Operation 1", "qty": 3, "pending_qty": 3}],
		)
		job_card = frappe.get_last_doc("Job Card", {"work_order": wo.name})
		job_card.update({"for_quantity": 3})
		job_card.append(
			"time_logs",
			{
				"from_time": add_to_date(now(), hours=3),
				"to_time": add_to_date(now(), hours=4),
				"completed_qty": 3,
			},
		)
		job_card.submit()

		corrective_job_card = make_corrective_job_card(
			job_card.name, operation=corrective_action.name, for_operation=job_card.operation
		)
		corrective_job_card.hour_rate = 80
		corrective_job_card.insert()
		corrective_job_card.append(
			"time_logs",
			{
				"from_time": add_to_date(now(), hours=4),
				"to_time": add_to_date(now(), hours=4, minutes=30),
				"completed_qty": 3,
			},
		)
		corrective_job_card.submit()
		wo.reload()

		stock_entry = make_stock_entry_for_wo(wo.name, "Manufacture", qty=4)
		self.assertEqual(stock_entry.additional_costs[1].amount, 52.5)

	def test_job_card_statuses(self):
		def assertStatus(status):
			jc.set_status()
			self.assertEqual(jc.status, status)

		jc = frappe.new_doc("Job Card")
		jc.process_loss_qty = 0
		jc.for_quantity = 2
		jc.transferred_qty = 1
		jc.total_completed_qty = 0
		assertStatus("Open")

		jc.transferred_qty = jc.for_quantity
		assertStatus("Material Transferred")

		jc.append("time_logs", {})
		assertStatus("Work In Progress")

		jc.docstatus = 1
		jc.total_completed_qty = jc.for_quantity
		assertStatus("Completed")

		jc.docstatus = 2
		assertStatus("Cancelled")

	def test_job_card_material_request_and_bom_details(self):
		from erpnext.stock.doctype.material_request.mapper import make_stock_entry

		create_bom_with_multiple_operations()
		work_order = make_wo_with_transfer_against_jc()

		job_card_name = frappe.db.get_value("Job Card", {"work_order": work_order.name}, "name")

		mr = make_material_request(job_card_name)
		mr.schedule_date = today()
		mr.submit()

		ste = make_stock_entry(mr.name)
		self.assertEqual(ste.purpose, "Material Transfer for Manufacture")
		self.assertEqual(ste.work_order, work_order.name)
		self.assertEqual(ste.job_card, job_card_name)
		self.assertEqual(ste.from_bom, 1.0)
		self.assertEqual(ste.bom_no, work_order.bom_no)

	def test_job_card_material_transfer_via_pick_list(self):
		from erpnext.stock.doctype.material_request.mapper import create_pick_list
		from erpnext.stock.doctype.pick_list.mapper import (
			create_stock_entry as create_stock_entry_from_pick_list,
		)

		create_bom_with_multiple_operations()
		work_order = make_wo_with_transfer_against_jc()

		for item in work_order.required_items:
			make_stock_entry(
				item_code=item.item_code,
				target=item.source_warehouse,
				qty=item.required_qty * 2,
				basic_rate=100,
			)

		job_card_name = frappe.db.get_value("Job Card", {"work_order": work_order.name}, "name")
		job_card = frappe.get_doc("Job Card", job_card_name)

		mr = make_material_request(job_card_name)
		mr.schedule_date = today()
		mr.submit()

		pick_list = create_pick_list(mr.name)
		pick_list.submit()

		ste = frappe.get_doc(create_stock_entry_from_pick_list(pick_list.as_dict()))
		self.assertEqual(ste.purpose, "Material Transfer for Manufacture")
		self.assertEqual(ste.job_card, job_card_name)
		self.assertEqual(ste.work_order, work_order.name)
		self.assertEqual(ste.fg_completed_qty, job_card.for_quantity)
		for row in ste.items:
			self.assertEqual(row.t_warehouse, job_card.wip_warehouse)
			self.assertTrue(row.job_card_item)

		ste.insert()
		ste.submit()

		job_card.reload()
		self.assertEqual(job_card.transferred_qty, job_card.for_quantity)

	def test_job_card_proccess_qty_and_completed_qty(self):
		from erpnext.manufacturing.doctype.routing.test_routing import (
			create_routing,
			setup_bom,
			setup_operations,
		)
		from erpnext.manufacturing.doctype.work_order.mapper import (
			make_stock_entry as make_stock_entry_for_wo,
		)
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		operations = [
			{"operation": "Test Operation A1", "workstation": "Test Workstation A", "time_in_mins": 30},
			{"operation": "Test Operation B1", "workstation": "Test Workstation A", "time_in_mins": 20},
		]

		warehouse = create_warehouse("Test Warehouse 123 for Job Card")

		setup_operations(operations)

		item_code = "Test Job Card Process Qty Item"
		for item in [item_code, item_code + "RM 1", item_code + "RM 2"]:
			if not frappe.db.exists("Item", item):
				make_item(
					item,
					{
						"item_name": item,
						"stock_uom": "Nos",
						"is_stock_item": 1,
					},
				)

		routing_doc = create_routing(routing_name="Testing Route", operations=operations)
		bom_doc = setup_bom(
			item_code=item_code,
			routing=routing_doc.name,
			raw_materials=[item_code + "RM 1", item_code + "RM 2"],
			source_warehouse=warehouse,
		)

		for row in bom_doc.items:
			make_stock_entry(
				item_code=row.item_code,
				target=row.source_warehouse,
				qty=10,
				basic_rate=100,
			)

		wo_doc = make_wo_order_test_record(
			production_item=item_code,
			bom_no=bom_doc.name,
			skip_transfer=1,
			wip_warehouse=warehouse,
			source_warehouse=warehouse,
		)

		for row in routing_doc.operations:
			self.assertEqual(row.sequence_id, row.idx)

		first_job_card = frappe.get_all(
			"Job Card",
			filters={"work_order": wo_doc.name, "sequence_id": 1},
			fields=["name"],
			order_by="sequence_id",
			limit=1,
		)[0].name

		jc = frappe.get_doc("Job Card", first_job_card)
		for row in jc.scheduled_time_logs:
			jc.append(
				"time_logs",
				{
					"from_time": row.from_time,
					"to_time": row.to_time,
					"time_in_mins": row.time_in_mins,
				},
			)

		jc.time_logs[0].completed_qty = 8
		jc.pending_qty = 0.0
		jc.save()
		jc.submit()

		self.assertEqual(jc.process_loss_qty, 2)
		self.assertEqual(jc.for_quantity, 10)

		second_job_card = frappe.get_all(
			"Job Card",
			filters={"work_order": wo_doc.name, "sequence_id": 2},
			fields=["name"],
			order_by="sequence_id",
			limit=1,
		)[0].name

		jc2 = frappe.get_doc("Job Card", second_job_card)
		for row in jc2.scheduled_time_logs:
			jc2.append(
				"time_logs",
				{
					"from_time": row.from_time,
					"to_time": row.to_time,
					"time_in_mins": row.time_in_mins,
				},
			)
		jc2.time_logs[0].completed_qty = 10

		self.assertRaises(frappe.ValidationError, jc2.save)

		jc2.load_from_db()
		for row in jc2.scheduled_time_logs:
			jc2.append(
				"time_logs",
				{
					"from_time": row.from_time,
					"to_time": row.to_time,
					"time_in_mins": row.time_in_mins,
				},
			)

		jc2.time_logs[0].completed_qty = 8
		jc2.save()
		jc2.submit()

		self.assertEqual(jc2.for_quantity, 10)
		self.assertEqual(jc2.process_loss_qty, 2)

		s = frappe.get_doc(make_stock_entry_for_wo(wo_doc.name, "Manufacture", 10))
		s.submit()

		self.assertEqual(s.process_loss_qty, 2)

		wo_doc.reload()
		for row in wo_doc.operations:
			self.assertEqual(row.completed_qty, 8)
			self.assertEqual(row.process_loss_qty, 2)

		self.assertEqual(wo_doc.produced_qty, 8)
		self.assertEqual(wo_doc.process_loss_qty, 2)
		self.assertEqual(wo_doc.status, "Completed")

	def make_two_operation_work_order(self, qty=10):
		from erpnext.manufacturing.doctype.routing.test_routing import (
			create_routing,
			setup_bom,
			setup_operations,
		)
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		operations = [
			{"operation": "Test Operation A1", "workstation": "Test Workstation A", "time_in_mins": 30},
			{"operation": "Test Operation B1", "workstation": "Test Workstation A", "time_in_mins": 20},
		]

		warehouse = create_warehouse("Test Warehouse 123 for Job Card")
		setup_operations(operations)

		item_code = "Test Job Card Process Qty Item"
		for item in [item_code, item_code + "RM 1", item_code + "RM 2"]:
			if not frappe.db.exists("Item", item):
				make_item(item, {"item_name": item, "stock_uom": "Nos", "is_stock_item": 1})

		routing_doc = create_routing(routing_name="Testing Route", operations=operations)
		bom_doc = setup_bom(
			item_code=item_code,
			routing=routing_doc.name,
			raw_materials=[item_code + "RM 1", item_code + "RM 2"],
			source_warehouse=warehouse,
		)

		for row in bom_doc.items:
			make_stock_entry(item_code=row.item_code, target=row.source_warehouse, qty=qty, basic_rate=100)

		return make_wo_order_test_record(
			production_item=item_code,
			bom_no=bom_doc.name,
			qty=qty,
			skip_transfer=1,
			wip_warehouse=warehouse,
			source_warehouse=warehouse,
		)

	def test_completion_qty_capped_by_previous_operation(self):
		wo_doc = self.make_two_operation_work_order()
		job_cards = frappe.get_all(
			"Job Card",
			filters={"work_order": wo_doc.name},
			fields=["name", "sequence_id"],
			order_by="sequence_id",
		)

		jc1 = frappe.get_doc("Job Card", job_cards[0].name)
		self.assertIsNone(jc1.get_max_completable_qty())

		jc1.append(
			"time_logs",
			{"from_time": now(), "to_time": add_to_date(now(), minutes=30), "completed_qty": 8},
		)
		jc1.save()
		jc1.submit()
		self.assertEqual(jc1.process_loss_qty, 2)

		jc2 = frappe.get_doc("Job Card", job_cards[1].name)
		self.assertEqual(jc2.get_max_completable_qty(), 8)

		jc2.append("time_logs", {"from_time": add_to_date(now(), minutes=40)})
		jc2.save()

		self.assertRaises(
			frappe.ValidationError,
			jc2.complete_job_card,
			qty=10,
			for_quantity=10,
			pending_qty=0,
			process_loss_qty=0,
			end_time=add_to_date(now(), minutes=70),
		)

		self.complete_second_operation_and_finish(wo_doc, jc2.name)

	def complete_second_operation_and_finish(self, wo_doc, job_card):
		from erpnext.manufacturing.doctype.work_order.mapper import (
			make_stock_entry as make_stock_entry_for_wo,
		)

		jc2 = frappe.get_doc("Job Card", job_card)
		jc2.time_logs[0].completed_qty = 7
		jc2.time_logs[0].to_time = add_to_date(now(), minutes=70)
		jc2.save()
		self.assertEqual(jc2.process_loss_qty, 3)
		jc2.submit()

		se = frappe.get_doc(make_stock_entry_for_wo(wo_doc.name, "Manufacture", 10))
		se.submit()

		self.assertEqual(se.process_loss_qty, 3)
		fg_qty = sum(d.qty for d in se.items if d.is_finished_item)
		self.assertEqual(flt(fg_qty), 7)

		wo_doc.reload()
		self.assertEqual(wo_doc.produced_qty, 7)
		self.assertEqual(wo_doc.process_loss_qty, 3)
		self.assertEqual(wo_doc.status, "Completed")

	def get_first_job_card(self, work_order):
		return frappe.get_doc(
			"Job Card",
			frappe.get_all(
				"Job Card",
				filters={"work_order": work_order},
				order_by="sequence_id, creation",
				limit=1,
				pluck="name",
			)[0],
		)

	def test_stock_uom_is_set_from_the_produced_item(self):
		work_order = make_wo_order_test_record(item="_Test FG Item 2", qty=5)

		job_card = self.get_first_job_card(work_order.name)
		item_code = job_card.finished_good or job_card.production_item

		self.assertEqual(job_card.stock_uom, frappe.db.get_value("Item", item_code, "stock_uom"))

	def test_completion_qty_reduces_for_quantity_without_process_loss(self):
		work_order = make_wo_order_test_record(item="_Test FG Item 2", qty=5)

		job_card = self.get_first_job_card(work_order.name)
		job_card.append("time_logs", {"from_time": "2024-03-01 08:00:00"})
		job_card.save()

		job_card.complete_job_card(
			qty=3,
			for_quantity=3,
			pending_qty=0,
			process_loss_qty=0,
			end_time="2024-03-01 09:00:00",
		)

		job_card.reload()
		self.assertEqual(flt(job_card.for_quantity), 3)
		self.assertEqual(flt(job_card.total_completed_qty), 3)
		self.assertEqual(flt(job_card.process_loss_qty), 0)

	def test_completion_qty_keeps_for_quantity_across_cycles(self):
		work_order = make_wo_order_test_record(item="_Test FG Item 2", qty=5)

		job_card = self.get_first_job_card(work_order.name)
		job_card.append("time_logs", {"from_time": "2024-03-02 08:00:00"})
		job_card.save()

		job_card.complete_job_card(
			qty=3,
			for_quantity=5,
			pending_qty=2,
			process_loss_qty=0,
			end_time="2024-03-02 09:00:00",
		)

		job_card.reload()
		self.assertEqual(flt(job_card.for_quantity), 5)
		self.assertEqual(flt(job_card.pending_qty), 2)
		self.assertEqual(flt(job_card.process_loss_qty), 0)

		job_card.append("time_logs", {"from_time": "2024-03-02 10:00:00"})
		job_card.save()

		job_card.complete_job_card(
			qty=2,
			for_quantity=2,
			pending_qty=0,
			process_loss_qty=0,
			end_time="2024-03-02 11:00:00",
		)

		job_card.reload()
		self.assertEqual(flt(job_card.for_quantity), 5)
		self.assertEqual(flt(job_card.total_completed_qty), 5)
		self.assertEqual(flt(job_card.process_loss_qty), 0)

	def test_op_cost_calculation(self):
		from erpnext.manufacturing.doctype.routing.test_routing import (
			create_routing,
			setup_bom,
			setup_operations,
		)
		from erpnext.manufacturing.doctype.work_order.mapper import (
			make_stock_entry as make_stock_entry_for_wo,
		)
		from erpnext.manufacturing.doctype.work_order.work_order import make_job_card
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		make_workstation(workstation_name="Test Workstation Z", hour_rate_rent=240)
		operations = [
			{"operation": "Test Operation A1", "workstation": "Test Workstation Z", "time_in_mins": 30},
		]

		warehouse = create_warehouse("Test Warehouse 123 for Job Card")
		setup_operations(operations)

		item_code = "Test Job Card Process Qty Item"
		for item in [item_code, item_code + "RM 1", item_code + "RM 2"]:
			if not frappe.db.exists("Item", item):
				make_item(
					item,
					{
						"item_name": item,
						"stock_uom": "Nos",
						"is_stock_item": 1,
					},
				)

		routing_doc = create_routing(routing_name="Testing Route", operations=operations)
		bom_doc = setup_bom(
			item_code=item_code,
			routing=routing_doc.name,
			raw_materials=[item_code + "RM 1", item_code + "RM 2"],
			source_warehouse=warehouse,
		)

		for row in bom_doc.items:
			make_stock_entry(
				item_code=row.item_code,
				target=row.source_warehouse,
				qty=10,
				basic_rate=100,
			)

		wo_doc = make_wo_order_test_record(
			production_item=item_code,
			bom_no=bom_doc.name,
			qty=10,
			skip_transfer=1,
			wip_warehouse=warehouse,
			source_warehouse=warehouse,
		)

		first_job_card = frappe.get_all(
			"Job Card",
			filters={"work_order": wo_doc.name, "sequence_id": 1},
			fields=["name"],
			order_by="sequence_id",
			limit=1,
		)[0].name

		jc = frappe.get_doc("Job Card", first_job_card)
		for _ in jc.scheduled_time_logs:
			jc.append(
				"time_logs",
				{
					"from_time": now(),
					"to_time": add_to_date(now(), minutes=1),
					"completed_qty": 4,
				},
			)
		jc.for_quantity = 4
		jc.save()
		jc.submit()

		s = frappe.get_doc(make_stock_entry_for_wo(wo_doc.name, "Manufacture", 4))
		s.submit()

		self.assertEqual(s.additional_costs[0].amount, 4)

		make_job_card(
			wo_doc.name,
			[
				{
					"name": wo_doc.operations[0].name,
					"operation": "Test Operation A1",
					"qty": 6,
					"pending_qty": 6,
				}
			],
		)

		job_card = frappe.get_last_doc("Job Card", {"work_order": wo_doc.name})
		job_card.append(
			"time_logs",
			{
				"from_time": add_to_date(now(), hours=1),
				"to_time": add_to_date(now(), hours=1, minutes=2),
				"completed_qty": 6,
			},
		)
		job_card.for_quantity = 6
		job_card.save()
		job_card.submit()

		s = frappe.get_doc(make_stock_entry_for_wo(wo_doc.name, "Manufacture", 6))
		self.assertEqual(s.additional_costs[0].amount, 8)

	def test_co_by_product_for_sfg_flow(self):
		from erpnext.manufacturing.doctype.operation.test_operation import make_operation

		frappe.db.set_value("UOM", "Nos", "must_be_whole_number", 0)

		def create_bom(raw_material, finished_good, scrap_item, submit=True):
			bom = frappe.new_doc("BOM")
			bom.company = "_Test Company"
			bom.item = finished_good
			bom.quantity = 1
			bom.append("items", {"item_code": raw_material, "qty": 1})
			bom.append(
				"secondary_items",
				{
					"item_code": scrap_item,
					"qty": 1,
					"process_loss_per": 10,
					"cost_allocation_per": 5,
					"secondary_item_type": "Scrap",
				},
			)
			if submit:
				bom.insert()
				bom.submit()

			return bom

		rm1 = create_item("RM 1")
		shared_scrap = create_item("Shared Scrap")
		sfg = create_item("SFG 1")
		sfg_bom = create_bom(rm1.name, sfg.name, shared_scrap.name)

		rm2 = create_item("RM 2")
		fg1 = create_item("FG 1")
		scrap_extra = create_item("Scrap Extra")
		fg_bom = create_bom(rm2.name, fg1.name, shared_scrap.name, submit=False)
		fg_bom.with_operations = 1
		fg_bom.track_semi_finished_goods = 1

		operation1 = {
			"operation": "Test Operation A",
			"workstation": "_Test Workstation A",
			"finished_good": sfg.name,
			"bom_no": sfg_bom.name,
			"finished_good_qty": 1,
			"sequence_id": 1,
			"time_in_mins": 60,
		}
		operation2 = {
			"operation": "Test Operation B",
			"workstation": "_Test Workstation A",
			"finished_good": fg1.name,
			"bom_no": fg_bom.name,
			"finished_good_qty": 1,
			"is_final_finished_good": 1,
			"sequence_id": 2,
			"time_in_mins": 60,
		}

		make_workstation(operation1)
		make_operation(operation1)
		make_operation(operation2)

		fg_bom.append("operations", operation1)
		fg_bom.append("operations", operation2)
		fg_bom.append("items", {"item_code": sfg.name, "qty": 1, "uom": "Nos", "operation_row_id": 2})
		fg_bom.insert()
		fg_bom.save()
		fg_bom.submit()

		work_order = make_wo_order_test_record(
			item=fg1.name,
			qty=10,
			source_warehouse="Stores - _TC",
			fg_warehouse="Finished Goods - _TC",
			bom_no=fg_bom.name,
			skip_transfer=1,
			do_not_save=True,
		)

		work_order.operations[0].time_in_mins = 60
		work_order.operations[1].time_in_mins = 60
		work_order.save()
		work_order.submit()

		job_card = frappe.get_doc(
			"Job Card",
			frappe.db.get_value(
				"Job Card", {"work_order": work_order.name, "operation": "Test Operation A"}, "name"
			),
		)
		job_card.append(
			"time_logs",
			{
				"from_time": "2009-01-01 12:06:25",
				"to_time": "2009-01-01 12:37:25",
				"completed_qty": job_card.for_quantity,
			},
		)
		job_card.append(
			"secondary_items",
			{"item_code": scrap_extra.name, "stock_qty": 5, "secondary_item_type": "Co-Product"},
		)
		job_card.submit()

		for row in sfg_bom.items:
			make_stock_entry(
				item_code=row.item_code,
				target="Stores - _TC",
				qty=10,
				basic_rate=100,
			)

		manufacturing_entry = frappe.get_doc(job_card.make_stock_entry_for_semi_fg_item())
		manufacturing_entry.submit()

		self.assertEqual(manufacturing_entry.items[2].item_code, shared_scrap.name)
		self.assertEqual(manufacturing_entry.items[2].qty, 9)
		self.assertEqual(flt(manufacturing_entry.items[2].basic_rate, 3), 5.556)
		self.assertEqual(manufacturing_entry.items[3].item_code, scrap_extra.name)
		self.assertEqual(manufacturing_entry.items[3].secondary_item_type, "Co-Product")
		self.assertEqual(manufacturing_entry.items[3].qty, 5)
		self.assertEqual(manufacturing_entry.items[3].basic_rate, 0)

		job_card = frappe.get_doc(
			"Job Card",
			frappe.db.get_value(
				"Job Card", {"work_order": work_order.name, "operation": "Test Operation B"}, "name"
			),
		)
		job_card.append(
			"time_logs",
			{
				"from_time": "2009-02-01 12:06:25",
				"to_time": "2009-02-01 12:37:25",
				"completed_qty": job_card.for_quantity,
			},
		)
		job_card.submit()

		for row in fg_bom.items:
			if row.item_code == sfg.name:
				continue

			make_stock_entry(
				item_code=row.item_code,
				target="Stores - _TC",
				qty=10,
				basic_rate=100,
			)

		manufacturing_entry = frappe.get_doc(job_card.make_stock_entry_for_semi_fg_item())
		manufacturing_entry.submit()

		sfg_row = next(row for row in manufacturing_entry.items if row.item_code == sfg.name)
		self.assertEqual(flt(sfg_row.basic_rate, 3), 95.0)

		self.assertEqual(manufacturing_entry.items[2].item_code, shared_scrap.name)
		self.assertEqual(manufacturing_entry.items[2].qty, 9)
		self.assertEqual(flt(manufacturing_entry.items[2].basic_rate, 3), 5.278)

	def test_semi_fg_produced_qty_across_split_job_cards(self):
		from erpnext.manufacturing.doctype.operation.test_operation import make_operation
		from erpnext.manufacturing.doctype.work_order.mapper import make_job_card
		from erpnext.stock.doctype.item.test_item import make_item

		warehouse = "Stores - _TC"
		rm = make_item("Split JC RM 1", {"is_stock_item": 1}).name
		fg = make_item("Split JC FG 1", {"is_stock_item": 1}).name

		fg_bom = frappe.new_doc(
			"BOM",
			company="_Test Company",
			item=fg,
			quantity=1,
			with_operations=1,
			track_semi_finished_goods=1,
		)
		fg_bom.append("items", {"item_code": rm, "qty": 1, "operation_row_id": 1})

		operation = {
			"operation": "Split JC Op A",
			"workstation": "_Test Workstation A",
			"finished_good": fg,
			"finished_good_qty": 1,
			"is_final_finished_good": 1,
			"sequence_id": 1,
			"time_in_mins": 60,
			"source_warehouse": warehouse,
			"fg_warehouse": warehouse,
			"skip_material_transfer": 1,
		}
		make_workstation(operation)
		make_operation(operation)
		fg_bom.append("operations", operation)
		fg_bom.insert()
		fg_bom.submit()

		work_order = make_wo_order_test_record(
			item=fg,
			qty=8,
			source_warehouse=warehouse,
			fg_warehouse=warehouse,
			bom_no=fg_bom.name,
			skip_transfer=1,
			do_not_save=True,
		)
		work_order.operations[0].time_in_mins = 60
		work_order.save()
		work_order.submit()

		make_stock_entry(item_code=rm, target=warehouse, qty=100, basic_rate=100)

		job_card = frappe.get_doc(
			"Job Card", frappe.db.get_value("Job Card", {"work_order": work_order.name}, "name")
		)
		job_card.for_quantity = 5
		job_card.append(
			"time_logs",
			{"from_time": "2024-02-01 08:00:00", "to_time": "2024-02-01 09:00:00", "completed_qty": 5},
		)
		job_card.save()
		job_card.submit()
		frappe.get_doc(job_card.make_stock_entry_for_semi_fg_item()).submit()

		work_order.reload()
		self.assertEqual(flt(work_order.produced_qty), 5)

		make_job_card(
			work_order.name,
			[
				{
					"name": work_order.operations[0].name,
					"operation": "Split JC Op A",
					"qty": 3,
					"pending_qty": 3,
					"skip_material_transfer": 1,
				}
			],
		)

		job_card = frappe.get_doc(
			"Job Card", frappe.db.get_value("Job Card", {"work_order": work_order.name, "docstatus": 0})
		)
		job_card.append(
			"time_logs",
			{
				"from_time": "2024-02-02 08:00:00",
				"to_time": "2024-02-02 09:00:00",
				"completed_qty": job_card.for_quantity,
			},
		)
		job_card.save()
		job_card.submit()
		frappe.get_doc(job_card.make_stock_entry_for_semi_fg_item()).submit()

		work_order.reload()
		self.assertEqual(flt(work_order.produced_qty), 8)
		self.assertEqual(work_order.status, "Completed")
		self.assertEqual(
			flt(frappe.db.get_value("Work Order Operation", work_order.operations[0].name, "completed_qty")),
			8,
		)

	def test_semi_fg_pending_qty_is_left_to_another_job_card(self):
		from erpnext.manufacturing.doctype.operation.test_operation import make_operation
		from erpnext.stock.doctype.item.test_item import make_item

		warehouse = "Stores - _TC"
		rm = make_item("Pending Qty RM 1", {"is_stock_item": 1}).name
		fg = make_item("Pending Qty FG 1", {"is_stock_item": 1}).name

		fg_bom = frappe.new_doc(
			"BOM",
			company="_Test Company",
			item=fg,
			quantity=1,
			with_operations=1,
			track_semi_finished_goods=1,
		)
		fg_bom.append("items", {"item_code": rm, "qty": 1, "operation_row_id": 1})

		operation = {
			"operation": "Pending Qty Op A",
			"workstation": "_Test Workstation A",
			"finished_good": fg,
			"finished_good_qty": 1,
			"is_final_finished_good": 1,
			"sequence_id": 1,
			"time_in_mins": 60,
			"source_warehouse": warehouse,
			"fg_warehouse": warehouse,
			"skip_material_transfer": 1,
		}

		make_workstation(operation)
		make_operation(operation)
		fg_bom.append("operations", operation)
		fg_bom.insert()
		fg_bom.submit()

		work_order = make_wo_order_test_record(
			item=fg,
			qty=5,
			source_warehouse=warehouse,
			fg_warehouse=warehouse,
			bom_no=fg_bom.name,
			skip_transfer=1,
			do_not_save=True,
		)
		work_order.operations[0].time_in_mins = 60
		work_order.save()
		work_order.submit()

		make_stock_entry(item_code=rm, target=warehouse, qty=100, basic_rate=100)

		job_card = self.get_first_job_card(work_order.name)
		job_card.append("time_logs", {"from_time": "2024-04-01 08:00:00"})
		job_card.save()

		job_card.complete_job_card(
			qty=3,
			for_quantity=5,
			pending_qty=2,
			process_loss_qty=0,
			end_time="2024-04-01 09:00:00",
		)

		job_card.reload()
		self.assertEqual(flt(job_card.for_quantity), 5)
		self.assertEqual(flt(job_card.pending_qty), 2)
		self.assertEqual(flt(job_card.process_loss_qty), 0)

		job_card.submit()
		self.assertEqual(job_card.status, "To Manufacture")

		manufacturing_entry = frappe.get_doc(job_card.make_stock_entry_for_semi_fg_item())
		finished_item = next(row for row in manufacturing_entry.items if row.is_finished_item)
		self.assertEqual(flt(finished_item.qty), 3)
		manufacturing_entry.submit()

		job_card.reload()
		self.assertEqual(flt(job_card.manufactured_qty), 3)
		self.assertEqual(job_card.status, "Completed")

	def test_semi_fg_process_loss_rolls_up_to_work_order(self):
		from erpnext.manufacturing.doctype.operation.test_operation import make_operation
		from erpnext.stock.doctype.item.test_item import make_item

		warehouse = "Stores - _TC"
		rm = make_item("Process Loss Rollup RM 1", {"is_stock_item": 1}).name
		fg = make_item("Process Loss Rollup FG 1", {"is_stock_item": 1}).name

		fg_bom = frappe.new_doc(
			"BOM",
			company="_Test Company",
			item=fg,
			quantity=1,
			with_operations=1,
			track_semi_finished_goods=1,
		)
		fg_bom.append("items", {"item_code": rm, "qty": 1, "operation_row_id": 1})

		operation = {
			"operation": "Process Loss Rollup Op A",
			"workstation": "_Test Workstation A",
			"finished_good": fg,
			"finished_good_qty": 1,
			"is_final_finished_good": 1,
			"sequence_id": 1,
			"time_in_mins": 60,
			"source_warehouse": warehouse,
			"fg_warehouse": warehouse,
			"skip_material_transfer": 1,
		}

		make_workstation(operation)
		make_operation(operation)
		fg_bom.append("operations", operation)
		fg_bom.insert()
		fg_bom.submit()

		work_order = make_wo_order_test_record(
			item=fg,
			qty=10,
			source_warehouse=warehouse,
			fg_warehouse=warehouse,
			bom_no=fg_bom.name,
			skip_transfer=1,
			do_not_save=True,
		)
		work_order.operations[0].time_in_mins = 60
		work_order.save()
		work_order.submit()

		make_stock_entry(item_code=rm, target=warehouse, qty=100, basic_rate=100)

		job_card = self.get_first_job_card(work_order.name)
		job_card.append("time_logs", {"from_time": "2024-05-01 08:00:00"})
		job_card.save()

		job_card.complete_job_card(
			qty=8,
			for_quantity=10,
			pending_qty=0,
			process_loss_qty=2,
			end_time="2024-05-01 09:00:00",
		)

		job_card.reload()
		self.assertEqual(flt(job_card.process_loss_qty), 2)

		job_card.submit()
		frappe.get_doc(job_card.make_stock_entry_for_semi_fg_item()).submit()

		self.assertEqual(
			flt(
				frappe.db.get_value("Work Order Operation", work_order.operations[0].name, "process_loss_qty")
			),
			2,
		)

		work_order.reload()
		self.assertEqual(flt(work_order.produced_qty), 8)
		self.assertEqual(flt(work_order.process_loss_qty), 2)
		self.assertEqual(work_order.status, "Completed")

	def test_semi_fg_process_loss_of_an_intermediate_operation_rolls_up_to_work_order(self):
		"""Loss booked by an earlier operation shrinks what the final operation can produce,
		so it has to show up on the work order even though the final operation loses nothing."""
		from erpnext.manufacturing.doctype.operation.test_operation import make_operation
		from erpnext.stock.doctype.item.test_item import make_item

		warehouse = "Stores - _TC"
		rm = make_item("Intermediate Loss RM 1", {"is_stock_item": 1}).name
		sfg = make_item("Intermediate Loss SFG 1", {"is_stock_item": 1}).name
		fg = make_item("Intermediate Loss FG 1", {"is_stock_item": 1}).name

		sfg_bom = frappe.new_doc("BOM", company="_Test Company", item=sfg, quantity=1)
		sfg_bom.append("items", {"item_code": rm, "qty": 1})
		sfg_bom.insert()
		sfg_bom.submit()

		fg_bom = frappe.new_doc(
			"BOM",
			company="_Test Company",
			item=fg,
			quantity=1,
			with_operations=1,
			track_semi_finished_goods=1,
		)

		operations = [
			{
				"operation": "Intermediate Loss Op A",
				"finished_good": sfg,
				"bom_no": sfg_bom.name,
				"sequence_id": 1,
			},
			{
				"operation": "Intermediate Loss Op B",
				"finished_good": fg,
				"is_final_finished_good": 1,
				"sequence_id": 2,
			},
		]

		for row in operations:
			row.update(
				{
					"workstation": "_Test Workstation A",
					"finished_good_qty": 1,
					"time_in_mins": 60,
					"source_warehouse": warehouse,
					"fg_warehouse": warehouse,
					"skip_material_transfer": 1,
				}
			)
			make_workstation(row)
			make_operation(row)
			fg_bom.append("operations", row)

		fg_bom.append("items", {"item_code": sfg, "qty": 1, "operation_row_id": 2})
		fg_bom.insert()
		fg_bom.submit()

		work_order = make_wo_order_test_record(
			item=fg,
			qty=10,
			source_warehouse=warehouse,
			fg_warehouse=warehouse,
			bom_no=fg_bom.name,
			skip_transfer=1,
			do_not_save=True,
		)
		for row in work_order.operations:
			row.time_in_mins = 60
		work_order.save()
		work_order.submit()

		make_stock_entry(item_code=rm, target=warehouse, qty=100, basic_rate=100)

		def get_job_card(operation):
			return frappe.get_doc(
				"Job Card",
				frappe.db.get_value(
					"Job Card",
					{"work_order": work_order.name, "operation": operation, "docstatus": 0},
					"name",
				),
			)

		jc_a = get_job_card("Intermediate Loss Op A")
		jc_a.append("time_logs", {"from_time": "2024-06-01 08:00:00"})
		jc_a.save()
		jc_a.complete_job_card(
			qty=8, for_quantity=10, pending_qty=0, process_loss_qty=2, end_time="2024-06-01 09:00:00"
		)
		jc_a.reload()
		jc_a.submit()
		frappe.get_doc(jc_a.make_stock_entry_for_semi_fg_item()).submit()

		work_order.reload()
		self.assertEqual(flt(work_order.process_loss_qty), 2)

		# Operation A handed over only 8 units, so the final operation works on 8.
		jc_b = get_job_card("Intermediate Loss Op B")
		jc_b.for_quantity = 8
		for row in jc_b.items:
			row.required_qty = 8
		jc_b.append(
			"time_logs",
			{"from_time": "2024-06-02 08:00:00", "to_time": "2024-06-02 09:00:00", "completed_qty": 8},
		)
		jc_b.save()
		jc_b.submit()
		frappe.get_doc(jc_b.make_stock_entry_for_semi_fg_item()).submit()

		work_order.reload()
		self.assertEqual(flt(work_order.produced_qty), 8)
		self.assertEqual(flt(work_order.process_loss_qty), 2)
		self.assertEqual(work_order.status, "Completed")

	def test_semi_fg_sequence_needs_previous_operations_manufactured(self):
		from erpnext.manufacturing.doctype.operation.test_operation import make_operation
		from erpnext.stock.doctype.item.test_item import make_item

		warehouse = "Stores - _TC"
		rm1 = make_item("Sequence Check RM 1", {"is_stock_item": 1}).name
		rm2 = make_item("Sequence Check RM 2", {"is_stock_item": 1}).name
		sfg1 = make_item("Sequence Check SFG 1", {"is_stock_item": 1}).name
		sfg2 = make_item("Sequence Check SFG 2", {"is_stock_item": 1}).name
		fg = make_item("Sequence Check FG 1", {"is_stock_item": 1}).name

		semi_fg_boms = {}
		for semi_fg_item, raw_material in ((sfg1, rm1), (sfg2, rm2)):
			bom = frappe.new_doc("BOM", company="_Test Company", item=semi_fg_item, quantity=1)
			bom.append("items", {"item_code": raw_material, "qty": 1})
			bom.insert()
			bom.submit()
			semi_fg_boms[semi_fg_item] = bom.name

		fg_bom = frappe.new_doc(
			"BOM",
			company="_Test Company",
			item=fg,
			quantity=1,
			with_operations=1,
			track_semi_finished_goods=1,
		)

		operations = [
			{
				"operation": "Sequence Check Op A",
				"finished_good": sfg1,
				"bom_no": semi_fg_boms[sfg1],
				"sequence_id": 1,
			},
			{
				"operation": "Sequence Check Op B",
				"finished_good": sfg2,
				"bom_no": semi_fg_boms[sfg2],
				"sequence_id": 1,
			},
			{
				"operation": "Sequence Check Op C",
				"finished_good": fg,
				"is_final_finished_good": 1,
				"sequence_id": 2,
			},
		]

		for row in operations:
			row.update(
				{
					"workstation": "_Test Workstation A",
					"finished_good_qty": 1,
					"time_in_mins": 60,
					"source_warehouse": warehouse,
					"fg_warehouse": warehouse,
					"skip_material_transfer": 1,
				}
			)

			make_workstation(row)
			make_operation(row)
			fg_bom.append("operations", row)

		fg_bom.append("items", {"item_code": sfg1, "qty": 1, "operation_row_id": 3})
		fg_bom.append("items", {"item_code": sfg2, "qty": 1, "operation_row_id": 3})
		fg_bom.insert()
		fg_bom.submit()

		work_order = make_wo_order_test_record(
			item=fg,
			qty=5,
			source_warehouse=warehouse,
			fg_warehouse=warehouse,
			bom_no=fg_bom.name,
			skip_transfer=1,
			do_not_save=True,
		)

		for row in work_order.operations:
			row.time_in_mins = 60

		work_order.save()
		work_order.submit()

		make_stock_entry(item_code=rm1, target=warehouse, qty=10, basic_rate=100)
		make_stock_entry(item_code=rm2, target=warehouse, qty=10, basic_rate=100)

		def get_job_card(operation):
			return frappe.get_doc(
				"Job Card",
				frappe.db.get_value(
					"Job Card",
					{"work_order": work_order.name, "operation": operation, "docstatus": 0},
					"name",
				),
			)

		def add_time_log(job_card, day, qty):
			job_card.append(
				"time_logs",
				{
					"from_time": f"2024-01-{day} 08:00:00",
					"to_time": f"2024-01-{day} 09:00:00",
					"completed_qty": qty,
				},
			)

		jc_a = get_job_card("Sequence Check Op A")
		jc_a.for_quantity = 3
		add_time_log(jc_a, "01", 3)
		jc_a.submit()

		jc_b = get_job_card("Sequence Check Op B")
		add_time_log(jc_b, "02", jc_b.for_quantity)
		jc_b.submit()
		frappe.get_doc(jc_b.make_stock_entry_for_semi_fg_item()).submit()

		jc_c = get_job_card("Sequence Check Op C")
		jc_c.for_quantity = 3
		add_time_log(jc_c, "03", 3)
		self.assertRaises(OperationSequenceError, jc_c.save)

		frappe.get_doc(jc_a.make_stock_entry_for_semi_fg_item()).submit()

		jc_c.reload()
		jc_c.for_quantity = 4
		add_time_log(jc_c, "03", 4)
		self.assertRaises(OperationSequenceError, jc_c.save)

		jc_c.reload()
		jc_c.for_quantity = 3
		add_time_log(jc_c, "03", 3)
		jc_c.submit()

		self.assertEqual(jc_c.docstatus, 1)

	def test_semi_fg_batch_auto_pull_on_manufacture(self):
		"""Batch produced by an operation should auto-pull into the next operation's
		semi-finished consumption row (skip-transfer Manufacture entry)."""
		from erpnext.manufacturing.doctype.operation.test_operation import make_operation
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.serial_batch_bundle import get_batches_from_bundle

		frappe.db.set_value("UOM", "Nos", "must_be_whole_number", 0)
		frappe.db.set_single_value("Manufacturing Settings", "make_serial_no_batch_from_work_order", 0)
		warehouse = "Stores - _TC"

		rm1 = make_item("Auto Pull RM 1", {"is_stock_item": 1}).name
		rm2 = make_item("Auto Pull RM 2", {"is_stock_item": 1}).name
		fg1 = make_item("Auto Pull FG 1", {"is_stock_item": 1}).name
		sfg = make_item(
			"Auto Pull SFG 1",
			{
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "AP-SFG-.#####",
			},
		).name

		sfg_bom = frappe.new_doc("BOM", company="_Test Company", item=sfg, quantity=1)
		sfg_bom.append("items", {"item_code": rm1, "qty": 1})
		sfg_bom.insert()
		sfg_bom.submit()

		fg_bom = frappe.new_doc(
			"BOM",
			company="_Test Company",
			item=fg1,
			quantity=1,
			with_operations=1,
			track_semi_finished_goods=1,
		)
		fg_bom.append("items", {"item_code": rm2, "qty": 1})

		operation1 = {
			"operation": "Auto Pull Op A",
			"workstation": "_Test Workstation A",
			"finished_good": sfg,
			"bom_no": sfg_bom.name,
			"finished_good_qty": 1,
			"sequence_id": 1,
			"time_in_mins": 60,
			"source_warehouse": warehouse,
			"fg_warehouse": warehouse,
			"skip_material_transfer": 1,
		}
		operation2 = {
			"operation": "Auto Pull Op B",
			"workstation": "_Test Workstation A",
			"finished_good": fg1,
			"finished_good_qty": 1,
			"is_final_finished_good": 1,
			"sequence_id": 2,
			"time_in_mins": 60,
			"source_warehouse": warehouse,
			"fg_warehouse": warehouse,
			"skip_material_transfer": 1,
		}

		make_workstation(operation1)
		make_operation(operation1)
		make_operation(operation2)

		fg_bom.append("operations", operation1)
		fg_bom.append("operations", operation2)
		fg_bom.append("items", {"item_code": sfg, "qty": 1, "uom": "Nos", "operation_row_id": 2})
		fg_bom.insert()
		fg_bom.submit()

		work_order = make_wo_order_test_record(
			item=fg1,
			qty=5,
			source_warehouse=warehouse,
			fg_warehouse=warehouse,
			bom_no=fg_bom.name,
			skip_transfer=1,
			do_not_save=True,
		)
		work_order.operations[0].time_in_mins = 60
		work_order.operations[1].time_in_mins = 60
		work_order.save()
		work_order.submit()

		make_stock_entry(item_code=rm1, target=warehouse, qty=10, basic_rate=100)
		make_stock_entry(item_code=rm2, target=warehouse, qty=10, basic_rate=100)

		# Operation A -> produces the SFG batch
		jc_a = frappe.get_doc(
			"Job Card",
			frappe.db.get_value(
				"Job Card", {"work_order": work_order.name, "operation": "Auto Pull Op A"}, "name"
			),
		)
		jc_a.append(
			"time_logs",
			{
				"from_time": "2024-01-01 08:00:00",
				"to_time": "2024-01-01 09:00:00",
				"completed_qty": jc_a.for_quantity,
			},
		)
		jc_a.submit()
		me_a = frappe.get_doc(jc_a.make_stock_entry_for_semi_fg_item())
		me_a.submit()

		me_a.reload()
		sfg_fg_row = next(r for r in me_a.items if r.is_finished_item and r.item_code == sfg)
		self.assertTrue(sfg_fg_row.serial_and_batch_bundle)
		produced_batches = get_batches_from_bundle(sfg_fg_row.serial_and_batch_bundle)

		# Operation B -> consumes the SFG; its batch should be auto-pulled from Operation A
		jc_b = frappe.get_doc(
			"Job Card",
			frappe.db.get_value(
				"Job Card", {"work_order": work_order.name, "operation": "Auto Pull Op B"}, "name"
			),
		)
		jc_b.append(
			"time_logs",
			{
				"from_time": "2024-02-01 08:00:00",
				"to_time": "2024-02-01 09:00:00",
				"completed_qty": jc_b.for_quantity,
			},
		)
		jc_b.submit()
		me_b = frappe.get_doc(jc_b.make_stock_entry_for_semi_fg_item())

		sfg_consume_row = next(r for r in me_b.items if r.item_code == sfg and r.s_warehouse)
		self.assertTrue(
			sfg_consume_row.serial_and_batch_bundle,
			"Previous operation's batch was not auto-pulled into the semi-finished consumption row",
		)
		consumed_batches = get_batches_from_bundle(sfg_consume_row.serial_and_batch_bundle)
		self.assertEqual(set(consumed_batches.keys()), set(produced_batches.keys()))

	def test_manufacture_entry_process_loss_not_taken_from_previous_operation(self):
		from erpnext.manufacturing.doctype.operation.test_operation import make_operation
		from erpnext.stock.doctype.item.test_item import make_item

		warehouse = "Stores - _TC"
		rm1 = make_item("PL Scope RM 1", {"is_stock_item": 1}).name
		rm2 = make_item("PL Scope RM 2", {"is_stock_item": 1}).name
		sfg = make_item("PL Scope SFG 1", {"is_stock_item": 1}).name
		fg1 = make_item("PL Scope FG 1", {"is_stock_item": 1}).name

		sfg_bom = frappe.new_doc("BOM", company="_Test Company", item=sfg, quantity=1)
		sfg_bom.append("items", {"item_code": rm1, "qty": 1})
		sfg_bom.insert()
		sfg_bom.submit()

		fg_bom = frappe.new_doc(
			"BOM",
			company="_Test Company",
			item=fg1,
			quantity=1,
			with_operations=1,
			track_semi_finished_goods=1,
		)
		operation1 = {
			"operation": "PL Scope Op A",
			"workstation": "_Test Workstation A",
			"finished_good": sfg,
			"bom_no": sfg_bom.name,
			"finished_good_qty": 1,
			"sequence_id": 1,
			"time_in_mins": 60,
			"source_warehouse": warehouse,
			"fg_warehouse": warehouse,
			"skip_material_transfer": 1,
		}
		operation2 = {
			"operation": "PL Scope Op B",
			"workstation": "_Test Workstation A",
			"finished_good": fg1,
			"finished_good_qty": 1,
			"is_final_finished_good": 1,
			"sequence_id": 2,
			"time_in_mins": 60,
			"source_warehouse": warehouse,
			"fg_warehouse": warehouse,
			"skip_material_transfer": 1,
		}
		make_workstation(operation1)
		make_operation(operation1)
		make_operation(operation2)
		fg_bom.append("operations", operation1)
		fg_bom.append("operations", operation2)
		fg_bom.append("items", {"item_code": rm2, "qty": 1})
		fg_bom.append("items", {"item_code": sfg, "qty": 1, "operation_row_id": 2})
		fg_bom.insert()
		fg_bom.submit()

		work_order = make_wo_order_test_record(
			item=fg1,
			qty=5,
			source_warehouse=warehouse,
			fg_warehouse=warehouse,
			bom_no=fg_bom.name,
			skip_transfer=1,
		)

		make_stock_entry(item_code=rm1, target=warehouse, qty=10, basic_rate=100)
		make_stock_entry(item_code=rm2, target=warehouse, qty=10, basic_rate=100)
		make_stock_entry(item_code=sfg, target=warehouse, qty=10, basic_rate=100)

		jc_a = frappe.get_doc(
			"Job Card",
			frappe.db.get_value(
				"Job Card", {"work_order": work_order.name, "operation": "PL Scope Op A"}, "name"
			),
		)
		jc_a.append(
			"time_logs",
			{"from_time": "2024-01-01 08:00:00", "to_time": "2024-01-01 09:00:00", "completed_qty": 3},
		)
		jc_a.pending_qty = 0
		jc_a.process_loss_qty = 2
		jc_a.submit()
		me_a = frappe.get_doc(jc_a.make_stock_entry_for_semi_fg_item())
		me_a.submit()
		self.assertEqual(flt(me_a.process_loss_qty), 2.0)

		jc_b = frappe.get_doc(
			"Job Card",
			frappe.db.get_value(
				"Job Card", {"work_order": work_order.name, "operation": "PL Scope Op B"}, "name"
			),
		)
		jc_b.append(
			"time_logs",
			{"from_time": "2024-02-01 08:00:00", "to_time": "2024-02-01 09:00:00", "completed_qty": 3},
		)
		jc_b.pending_qty = 2
		jc_b.submit()
		me_b = frappe.get_doc(jc_b.make_stock_entry_for_semi_fg_item())

		# operation A's loss must not leak into operation B's entry
		self.assertEqual(flt(me_b.process_loss_qty), 0.0)
		fg_row = next(row for row in me_b.items if row.is_finished_item)
		self.assertEqual(flt(fg_row.qty), 3.0)
		me_b.submit()

	def make_semi_fg_work_order(self, prefix, qty=5):
		"""Two-operation semi FG work order: Op A makes the SFG from RM 1, final Op B
		consumes it. Both operations skip material transfer; stock is pre-seeded."""
		from erpnext.manufacturing.doctype.operation.test_operation import make_operation
		from erpnext.stock.doctype.item.test_item import make_item

		warehouse = "Stores - _TC"
		rm1 = make_item(f"{prefix} RM 1", {"is_stock_item": 1}).name
		rm2 = make_item(f"{prefix} RM 2", {"is_stock_item": 1}).name
		sfg = make_item(f"{prefix} SFG 1", {"is_stock_item": 1}).name
		fg1 = make_item(f"{prefix} FG 1", {"is_stock_item": 1}).name

		sfg_bom = frappe.new_doc("BOM", company="_Test Company", item=sfg, quantity=1)
		sfg_bom.append("items", {"item_code": rm1, "qty": 1})
		sfg_bom.insert()
		sfg_bom.submit()

		fg_bom = frappe.new_doc(
			"BOM",
			company="_Test Company",
			item=fg1,
			quantity=1,
			with_operations=1,
			track_semi_finished_goods=1,
		)
		operation1 = {
			"operation": f"{prefix} Op A",
			"workstation": "_Test Workstation A",
			"finished_good": sfg,
			"bom_no": sfg_bom.name,
			"finished_good_qty": 1,
			"sequence_id": 1,
			"time_in_mins": 60,
			"source_warehouse": warehouse,
			"fg_warehouse": warehouse,
			"skip_material_transfer": 1,
		}
		operation2 = {
			"operation": f"{prefix} Op B",
			"workstation": "_Test Workstation A",
			"finished_good": fg1,
			"finished_good_qty": 1,
			"is_final_finished_good": 1,
			"sequence_id": 2,
			"time_in_mins": 60,
			"source_warehouse": warehouse,
			"fg_warehouse": warehouse,
			"skip_material_transfer": 1,
		}
		make_workstation(operation1)
		make_operation(operation1)
		make_operation(operation2)
		fg_bom.append("operations", operation1)
		fg_bom.append("operations", operation2)
		fg_bom.append("items", {"item_code": rm2, "qty": 1})
		fg_bom.append("items", {"item_code": sfg, "qty": 1, "operation_row_id": 2})
		fg_bom.insert()
		fg_bom.submit()

		work_order = make_wo_order_test_record(
			item=fg1,
			qty=qty,
			source_warehouse=warehouse,
			fg_warehouse=warehouse,
			bom_no=fg_bom.name,
			skip_transfer=1,
		)

		for item_code in (rm1, rm2, sfg):
			make_stock_entry(item_code=item_code, target=warehouse, qty=10, basic_rate=100)

		return work_order

	def get_semi_fg_job_card(self, work_order, operation):
		return frappe.get_doc(
			"Job Card",
			frappe.db.get_value("Job Card", {"work_order": work_order.name, "operation": operation}, "name"),
		)

	def test_partial_manufacture_entry_then_finish(self):
		work_order = self.make_semi_fg_work_order("PL Partial")

		jc_a = self.get_semi_fg_job_card(work_order, "PL Partial Op A")
		jc_a.append(
			"time_logs",
			{"from_time": "2024-01-01 08:00:00", "to_time": "2024-01-01 09:00:00", "completed_qty": 5},
		)
		jc_a.submit()
		frappe.get_doc(jc_a.make_stock_entry_for_semi_fg_item()).submit()

		jc_b = self.get_semi_fg_job_card(work_order, "PL Partial Op B")
		jc_b.append(
			"time_logs",
			{"from_time": "2024-02-01 08:00:00", "to_time": "2024-02-01 09:00:00", "completed_qty": 3},
		)
		jc_b.pending_qty = 0
		jc_b.process_loss_qty = 2
		jc_b.submit()

		# book 1 of the 3 finished units now; the full process loss goes with this first entry,
		# so it accounts for 3 of 5 and its materials are trimmed to the same share
		first = frappe.get_doc(jc_b.make_stock_entry_for_semi_fg_item())
		fg_row = next(row for row in first.items if row.is_finished_item)
		fg_row.qty = 1
		for row in first.items:
			if row.s_warehouse and not row.is_finished_item:
				row.qty = flt(row.qty) * 3 / 5
		first.save()
		first.submit()

		# the follow-up entry must be generated net of the already-booked loss and still submit
		jc_b.reload()
		second = frappe.get_doc(jc_b.make_stock_entry_for_semi_fg_item())
		fg_row = next(row for row in second.items if row.is_finished_item)
		self.assertEqual(flt(fg_row.qty), 2.0)
		self.assertEqual(flt(second.process_loss_qty), 0.0)
		second.submit()

		jc_b.reload()
		self.assertEqual(flt(jc_b.manufactured_qty), 3.0)

		# across both entries, consumption adds up to the job card's requirement of 5, no more
		consumed = frappe.get_all(
			"Stock Entry Detail",
			filters={"parent": ["in", [first.name, second.name]], "s_warehouse": ["is", "set"]},
			fields=["item_code", {"SUM": "qty", "as": "qty"}],
			group_by="item_code",
		)
		self.assertTrue(consumed)
		for row in consumed:
			self.assertEqual(flt(row.qty), 5.0, f"{row.item_code} mis-consumed across partial entries")

	def test_update_after_submit_keeps_manufacture_entry_intact(self):
		work_order = self.make_semi_fg_work_order("PL Update")

		jc_a = self.get_semi_fg_job_card(work_order, "PL Update Op A")
		jc_a.append(
			"time_logs",
			{"from_time": "2024-01-01 08:00:00", "to_time": "2024-01-01 09:00:00", "completed_qty": 3},
		)
		jc_a.pending_qty = 0
		jc_a.process_loss_qty = 2
		jc_a.submit()

		entry = frappe.get_doc(jc_a.make_stock_entry_for_semi_fg_item())
		entry.submit()

		if not frappe.db.exists("Print Heading", "_Test SFG Heading"):
			frappe.get_doc({"doctype": "Print Heading", "print_heading": "_Test SFG Heading"}).insert()

		entry.reload()
		entry.select_print_heading = "_Test SFG Heading"
		entry.save()

		entry.reload()
		self.assertEqual(flt(entry.process_loss_qty), 2.0)

	def test_stale_manufacture_draft_cannot_over_produce_without_operation_bom(self):
		work_order = self.make_semi_fg_work_order("PL NoBom")

		jc_a = self.get_semi_fg_job_card(work_order, "PL NoBom Op A")
		jc_a.append(
			"time_logs",
			{"from_time": "2024-01-01 08:00:00", "to_time": "2024-01-01 09:00:00", "completed_qty": 5},
		)
		jc_a.submit()
		frappe.get_doc(jc_a.make_stock_entry_for_semi_fg_item()).submit()

		# Op B has no operation BOM, so its entries carry no For Quantity to validate against
		jc_b = self.get_semi_fg_job_card(work_order, "PL NoBom Op B")
		jc_b.append(
			"time_logs",
			{"from_time": "2024-02-01 08:00:00", "to_time": "2024-02-01 09:00:00", "completed_qty": 3},
		)
		jc_b.pending_qty = 0
		jc_b.process_loss_qty = 2
		jc_b.submit()

		draft_one = frappe.get_doc(jc_b.make_stock_entry_for_semi_fg_item())
		draft_two = frappe.get_doc(jc_b.make_stock_entry_for_semi_fg_item())

		draft_one.submit()

		stale = frappe.get_doc("Stock Entry", draft_two.name)
		self.assertRaises(frappe.ValidationError, stale.submit)

	def test_semi_fg_auto_pull_with_uom_conversion(self):
		from erpnext.manufacturing.doctype.operation.test_operation import make_operation
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_entry.services.manufacturing import (
			set_previous_operation_serial_batch,
		)
		from erpnext.stock.serial_batch_bundle import get_batches_from_bundle

		frappe.db.set_value("UOM", "Nos", "must_be_whole_number", 0)
		frappe.db.set_single_value("Manufacturing Settings", "make_serial_no_batch_from_work_order", 0)
		warehouse = "Stores - _TC"

		rm1 = make_item("UOM Pull RM 1", {"is_stock_item": 1}).name
		rm2 = make_item("UOM Pull RM 2", {"is_stock_item": 1}).name
		fg1 = make_item("UOM Pull FG 1", {"is_stock_item": 1}).name
		sfg = make_item(
			"UOM Pull SFG 1",
			{
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "UP-SFG-.#####",
				"uoms": [{"uom": "Box", "conversion_factor": 5}],
			},
		).name

		sfg_bom = frappe.new_doc("BOM", company="_Test Company", item=sfg, quantity=1)
		sfg_bom.append("items", {"item_code": rm1, "qty": 1})
		sfg_bom.insert()
		sfg_bom.submit()

		fg_bom = frappe.new_doc(
			"BOM",
			company="_Test Company",
			item=fg1,
			quantity=1,
			with_operations=1,
			track_semi_finished_goods=1,
		)
		fg_bom.append("items", {"item_code": rm2, "qty": 1})

		operation1 = {
			"operation": "UOM Pull Op A",
			"workstation": "_Test Workstation A",
			"finished_good": sfg,
			"bom_no": sfg_bom.name,
			"finished_good_qty": 1,
			"sequence_id": 1,
			"time_in_mins": 60,
			"source_warehouse": warehouse,
			"fg_warehouse": warehouse,
			"skip_material_transfer": 1,
		}
		operation2 = {
			"operation": "UOM Pull Op B",
			"workstation": "_Test Workstation A",
			"finished_good": fg1,
			"finished_good_qty": 1,
			"is_final_finished_good": 1,
			"sequence_id": 2,
			"time_in_mins": 60,
			"source_warehouse": warehouse,
			"fg_warehouse": warehouse,
			"skip_material_transfer": 1,
		}

		make_workstation(operation1)
		make_operation(operation1)
		make_operation(operation2)

		fg_bom.append("operations", operation1)
		fg_bom.append("operations", operation2)
		fg_bom.append("items", {"item_code": sfg, "qty": 1, "uom": "Nos", "operation_row_id": 2})
		fg_bom.insert()
		fg_bom.submit()

		work_order = make_wo_order_test_record(
			item=fg1,
			qty=5,
			source_warehouse=warehouse,
			fg_warehouse=warehouse,
			bom_no=fg_bom.name,
			skip_transfer=1,
			do_not_save=True,
		)
		work_order.operations[0].time_in_mins = 60
		work_order.operations[1].time_in_mins = 60
		work_order.save()
		work_order.submit()

		make_stock_entry(item_code=rm1, target=warehouse, qty=10, basic_rate=100)
		make_stock_entry(item_code=sfg, target=warehouse, qty=5, basic_rate=100, posting_date="2024-01-01")

		jc_a = frappe.get_doc(
			"Job Card",
			frappe.db.get_value(
				"Job Card", {"work_order": work_order.name, "operation": "UOM Pull Op A"}, "name"
			),
		)
		jc_a.append(
			"time_logs",
			{
				"from_time": "2024-02-01 08:00:00",
				"to_time": "2024-02-01 09:00:00",
				"completed_qty": jc_a.for_quantity,
			},
		)
		jc_a.submit()
		me_a = frappe.get_doc(jc_a.make_stock_entry_for_semi_fg_item())
		me_a.submit()
		me_a.reload()

		sfg_fg_row = next(r for r in me_a.items if r.is_finished_item and r.item_code == sfg)
		produced_batches = get_batches_from_bundle(sfg_fg_row.serial_and_batch_bundle)

		se = frappe.new_doc("Stock Entry")
		se.company = "_Test Company"
		se.purpose = "Material Transfer"
		se.work_order = work_order.name
		se.set_stock_entry_type()
		row = se.append(
			"items",
			{
				"item_code": sfg,
				"qty": 1,
				"uom": "Box",
				"conversion_factor": 5,
				"s_warehouse": warehouse,
				"t_warehouse": "_Test Warehouse - _TC",
			},
		)
		set_previous_operation_serial_batch(se, row)

		self.assertTrue(row.serial_and_batch_bundle)
		self.assertEqual(
			abs(frappe.db.get_value("Serial and Batch Bundle", row.serial_and_batch_bundle, "total_qty")),
			5.0,
		)

		se.save()
		se.submit()
		se.reload()

		row = se.items[0]
		consumed_batches = get_batches_from_bundle(row.serial_and_batch_bundle)
		self.assertEqual(set(consumed_batches.keys()), set(produced_batches.keys()))
		self.assertEqual(abs(sum(consumed_batches.values())), 5.0)

	def test_secondary_items_without_sfg(self):
		for row in frappe.get_doc("BOM", self.work_order.bom_no).items:
			make_stock_entry(
				item_code=row.item_code,
				target="_Test Warehouse - _TC",
				qty=10,
				basic_rate=100,
			)

		job_card = frappe.get_last_doc("Job Card", {"work_order": self.work_order.name})
		job_card.append(
			"secondary_items", {"item_code": "_Test Item", "stock_qty": 2, "secondary_item_type": "Scrap"}
		)
		job_card.append(
			"time_logs",
			{
				"from_time": "2009-01-01 12:06:25",
				"to_time": "2009-01-01 12:37:25",
				"completed_qty": job_card.for_quantity,
			},
		)
		job_card.save()
		job_card.submit()

		from erpnext.manufacturing.doctype.work_order.mapper import (
			make_stock_entry as make_stock_entry_for_wo,
		)

		s = frappe.get_doc(make_stock_entry_for_wo(self.work_order.name, "Manufacture"))
		s.submit()

		self.assertEqual(s.items[3].item_code, "_Test Item")
		self.assertEqual(s.items[3].transfer_qty, 2)

		frappe.db.set_value(
			"Stock Entry Detail",
			s.items[3].name,
			{"secondary_item_type": None, "is_legacy_scrap_item": 1},
		)

		from erpnext.stock.doctype.stock_entry.services.manufacturing import ManufactureStockEntry

		stock_entry = frappe.get_doc({"doctype": "Stock Entry", "work_order": self.work_order.name})
		used_secondary_items = ManufactureStockEntry(stock_entry).get_used_secondary_items()
		self.assertEqual(used_secondary_items[("_Test Item", "Scrap")], 2)

	@ERPNextTestSuite.change_settings(
		"Manufacturing Settings", {"overproduction_percentage_for_work_order": 100}
	)
	def test_operating_cost_with_overproduction(self):
		from erpnext.manufacturing.doctype.routing.test_routing import (
			create_routing,
			setup_bom,
			setup_operations,
		)
		from erpnext.manufacturing.doctype.work_order.mapper import (
			make_stock_entry as make_stock_entry_for_wo,
		)
		from erpnext.manufacturing.doctype.work_order.work_order import make_job_card
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		workstation = make_workstation(
			workstation_name="Test Workstation for Overproduction", hour_rate_rent=10, hour_rate_labour=10
		)
		operations = [
			{"operation": "Test Operation 1", "workstation": workstation.name, "time_in_mins": 30},
			{"operation": "Test Operation 2", "workstation": workstation.name, "time_in_mins": 30},
		]
		warehouse = create_warehouse("Test Warehouse for Overproduction")
		setup_operations(operations)

		fg = make_item("Test FG for Overproduction", {"stock_uom": "Nos", "is_stock_item": 1})
		rm = make_item("Test RM for Overproduction", {"stock_uom": "Nos", "is_stock_item": 1})

		routing_doc = create_routing(routing_name="Testing Route", operations=operations)
		bom_doc = setup_bom(
			item_code=fg.name,
			routing=routing_doc.name,
			raw_materials=[rm.name],
			source_warehouse=warehouse,
		)

		for row in bom_doc.items:
			make_stock_entry(
				item_code=row.item_code,
				target=row.source_warehouse,
				qty=100,
				basic_rate=100,
			)

		wo_doc = make_wo_order_test_record(
			production_item=fg.name,
			bom_no=bom_doc.name,
			qty=10,
			skip_transfer=1,
			source_warehouse=warehouse,
		)

		first_operation = frappe.get_all(
			"Job Card",
			filters={"work_order": wo_doc.name, "sequence_id": 1},
			fields=["name"],
			order_by="sequence_id",
			limit=1,
		)[0].name

		jc = frappe.get_doc("Job Card", first_operation)
		from_time = add_to_date(now(), days=1)
		for _ in jc.scheduled_time_logs:
			jc.append(
				"time_logs",
				{
					"from_time": from_time,
					"to_time": add_to_date(from_time, days=1),
					"completed_qty": 4,
				},
			)
		jc.for_quantity = 4
		jc.save()
		jc.submit()

		second_operation = frappe.get_all(
			"Job Card",
			filters={"work_order": wo_doc.name, "sequence_id": 2},
			fields=["name"],
			order_by="sequence_id",
			limit=1,
		)[0].name

		jc = frappe.get_doc("Job Card", second_operation)
		from_time = add_to_date(now(), days=2)
		for _ in jc.scheduled_time_logs:
			jc.append(
				"time_logs",
				{
					"from_time": from_time,
					"to_time": add_to_date(from_time, days=2),
					"completed_qty": 4,
				},
			)
		jc.for_quantity = 4
		jc.save()
		jc.submit()

		s = frappe.get_doc(make_stock_entry_for_wo(wo_doc.name, "Manufacture", 6))  # overproduction
		s.submit()

		self.assertEqual(s.additional_costs[0].amount, 240)
		self.assertEqual(s.additional_costs[1].amount, 240)
		self.assertEqual(s.additional_costs[2].amount, 480)
		self.assertEqual(s.additional_costs[3].amount, 480)

		make_job_card(
			wo_doc.name,
			[
				{
					"name": wo_doc.operations[0].name,
					"operation": "Test Operation 1",
					"qty": 2,
					"pending_qty": 2,
				}
			],
		)

		job_card = frappe.get_last_doc("Job Card", {"work_order": wo_doc.name})
		from_time = add_to_date(now(), days=4)
		job_card.append(
			"time_logs",
			{
				"from_time": from_time,
				"to_time": add_to_date(from_time, days=1),
				"completed_qty": 2,
			},
		)
		job_card.for_quantity = 2
		job_card.save()
		job_card.submit()

		make_job_card(
			wo_doc.name,
			[
				{
					"name": wo_doc.operations[1].name,
					"operation": "Test Operation 2",
					"qty": 2,
					"pending_qty": 2,
				}
			],
		)

		job_card = frappe.get_last_doc("Job Card", {"work_order": wo_doc.name})
		from_time = add_to_date(now(), days=5)
		job_card.append(
			"time_logs",
			{
				"from_time": from_time,
				"to_time": add_to_date(from_time, days=2),
				"completed_qty": 2,
			},
		)
		job_card.for_quantity = 2
		job_card.save()
		job_card.submit()

		s2 = frappe.get_doc(make_stock_entry_for_wo(wo_doc.name, "Manufacture", 1))
		s2.submit()

		self.assertEqual(s2.additional_costs[0].amount, 120)
		self.assertEqual(s2.additional_costs[1].amount, 120)
		self.assertEqual(s2.additional_costs[2].amount, 240)
		self.assertEqual(s2.additional_costs[3].amount, 240)

		make_job_card(
			wo_doc.name,
			[
				{
					"name": wo_doc.operations[0].name,
					"operation": "Test Operation 1",
					"qty": 2,
					"pending_qty": 2,
				}
			],
		)

		job_card = frappe.get_last_doc("Job Card", {"work_order": wo_doc.name})
		from_time = add_to_date(now(), days=7)
		job_card.append(
			"time_logs",
			{
				"from_time": from_time,
				"to_time": add_to_date(from_time, days=1),
				"completed_qty": 2,
			},
		)
		job_card.for_quantity = 2
		job_card.save()
		job_card.submit()

		make_job_card(
			wo_doc.name,
			[
				{
					"name": wo_doc.operations[1].name,
					"operation": "Test Operation 2",
					"qty": 2,
					"pending_qty": 2,
				}
			],
		)

		job_card = frappe.get_last_doc("Job Card", {"work_order": wo_doc.name})
		from_time = add_to_date(now(), days=8)
		job_card.append(
			"time_logs",
			{
				"from_time": from_time,
				"to_time": add_to_date(from_time, days=2),
				"completed_qty": 2,
			},
		)
		job_card.for_quantity = 2
		job_card.save()
		job_card.submit()

		s = frappe.get_doc(make_stock_entry_for_wo(wo_doc.name, "Manufacture", 2))
		s.submit()

		self.assertEqual(s.additional_costs[0].amount, 240)
		self.assertEqual(s.additional_costs[1].amount, 240)
		self.assertEqual(s.additional_costs[2].amount, 480)
		self.assertEqual(s.additional_costs[3].amount, 480)

		s2.cancel()

		s = frappe.get_doc(make_stock_entry_for_wo(wo_doc.name, "Manufacture", 3))
		s.submit()

		self.assertEqual(s.additional_costs[0].amount, 240)
		self.assertEqual(s.additional_costs[1].amount, 240)
		self.assertEqual(s.additional_costs[2].amount, 480)
		self.assertEqual(s.additional_costs[3].amount, 480)


def create_bom_with_multiple_operations():
	"Create a BOM with multiple operations and Material Transfer against Job Card"
	from erpnext.manufacturing.doctype.operation.test_operation import make_operation

	test_record = frappe.get_test_records("BOM")[2]
	bom_doc = frappe.get_doc(test_record)

	row = {
		"operation": "Test Operation A",
		"workstation": "_Test Workstation A",
		"hour_rate_rent": 300,
		"time_in_mins": 60,
	}
	make_workstation(row)
	make_operation(row)

	bom_doc.append(
		"operations",
		{
			"operation": "Test Operation A",
			"description": "Test Operation A",
			"workstation": "_Test Workstation A",
			"hour_rate": 300,
			"time_in_mins": 60,
			"operating_cost": 100,
		},
	)

	bom_doc.transfer_material_against = "Job Card"
	bom_doc.save()
	bom_doc.submit()

	return bom_doc


def make_wo_with_transfer_against_jc():
	"Create a WO with multiple operations and Material Transfer against Job Card"

	work_order = make_wo_order_test_record(
		item="_Test FG Item 2",
		qty=4,
		transfer_material_against="Job Card",
		source_warehouse="Stores - _TC",
		do_not_submit=True,
	)
	work_order.required_items[0].operation = "Test Operation A"
	work_order.required_items[1].operation = "_Test Operation 1"
	work_order.submit()

	return work_order


def create_semi_fg_bom(semi_fg_item, raw_item, inspection_required):
	bom = frappe.new_doc("BOM")
	bom.company = "Wind Power LLC"
	bom.item = semi_fg_item
	bom.quantity = 1
	bom.inspection_required = inspection_required
	bom.append("items", {"item_code": raw_item, "qty": 1})
	bom.submit()
	return bom.name


class TestJobCardLogic(ERPNextTestSuite):
	"""Field-level validations and pure quantity/capacity helpers, exercised on the
	document directly so they don't need a Work Order / BOM (the integration suite does)."""

	def test_processing_a_submitted_or_cancelled_card_is_blocked(self):
		submitted = frappe.new_doc("Job Card")
		submitted.docstatus = 1
		self.assertRaises(frappe.ValidationError, submitted.validate_docstatus)

		cancelled = frappe.new_doc("Job Card")
		cancelled.docstatus = 2
		self.assertRaises(frappe.ValidationError, cancelled.validate_docstatus)

	def test_complete_job_card_qty_guards(self):
		jc = frappe.new_doc("Job Card")
		jc.for_quantity = 5
		jc.validate_complete_job_card_qty(frappe._dict(pending_qty=3))  # within range -> passes
		self.assertRaises(
			frappe.ValidationError, jc.validate_complete_job_card_qty, frappe._dict(pending_qty=-1)
		)
		self.assertRaises(
			frappe.ValidationError, jc.validate_complete_job_card_qty, frappe._dict(process_loss_qty=-1)
		)
		self.assertRaises(
			frappe.ValidationError, jc.validate_complete_job_card_qty, frappe._dict(pending_qty=10)
		)

	def test_qty_in_messages_carries_the_uom(self):
		jc = frappe.new_doc("Job Card")
		jc.stock_uom = "Nos"

		self.assertEqual(jc.get_qty_with_uom(5), "5.0 Nos")
		self.assertEqual(jc.get_qty_with_uom(0), "0.0 Nos")

	def test_completion_qty_split_must_add_up(self):
		jc = frappe.new_doc("Job Card")
		jc.for_quantity = 5

		# 3 completed + 2 pending + 0 lost == 5 to manufacture -> passes
		jc.validate_complete_job_card_qty(
			frappe._dict(for_quantity=5, qty=3, pending_qty=2, process_loss_qty=0)
		)

		self.assertRaises(
			frappe.ValidationError,
			jc.validate_complete_job_card_qty,
			frappe._dict(for_quantity=3, qty=3, pending_qty=2, process_loss_qty=0),
		)

	def test_completed_qty_must_reconcile_with_for_quantity(self):
		jc = frappe.new_doc("Job Card")
		jc.for_quantity = 10
		jc.total_completed_qty = 6
		jc.process_loss_qty = 0
		jc.pending_qty = 0
		# 6 + 0 + 0 != 10 -> throws
		self.assertRaises(frappe.ValidationError, jc.validate_completed_qty_matches_for_quantity)
		# completed + loss + pending == for_quantity -> passes
		jc.pending_qty = 4
		jc.validate_completed_qty_matches_for_quantity()

	def test_set_process_loss(self):
		jc = frappe.new_doc("Job Card")
		jc.for_quantity = 10
		jc.total_completed_qty = 6
		jc.pending_qty = 1
		jc.set_process_loss()
		self.assertEqual(jc.process_loss_qty, 3)  # 10 - 6 - 1

		# no loss when nothing completed yet
		nothing_done = frappe.new_doc("Job Card")
		nothing_done.for_quantity = 10
		nothing_done.total_completed_qty = 0
		nothing_done.set_process_loss()
		self.assertEqual(nothing_done.process_loss_qty, 0)

	def test_capacity_overlap_detection(self):
		jc = frappe.new_doc("Job Card")
		sequential = [
			{"from_time": "2026-01-01 10:00:00", "to_time": "2026-01-01 11:00:00"},
			{"from_time": "2026-01-01 11:00:00", "to_time": "2026-01-01 12:00:00"},
		]
		overlapping = [
			{"from_time": "2026-01-01 10:00:00", "to_time": "2026-01-01 11:00:00"},
			{"from_time": "2026-01-01 10:30:00", "to_time": "2026-01-01 11:30:00"},
		]
		# sequential logs share one capacity slot; overlapping logs need two
		self.assertEqual(len(jc.get_alloted_capacity(sequential)), 1)
		self.assertEqual(len(jc.get_alloted_capacity(overlapping)), 2)
		# capacity 1 overlaps with any log; capacity 2 only when both slots are taken
		self.assertTrue(jc.has_overlap(1, sequential))
		self.assertFalse(jc.has_overlap(2, sequential))
		self.assertTrue(jc.has_overlap(2, overlapping))

	def test_previous_operation_shortfall_from_process_loss_gets_the_right_message(self):
		jc = frappe.new_doc("Job Card")
		jc.operation = "_Test Painting"
		jc.stock_uom = "Nos"
		row = frappe._dict(
			operation="_Test Assembly", manufactured_qty=8, process_loss_qty=2, finished_good=None
		)

		with self.assertRaises(OperationSequenceError) as loss_error:
			jc.validate_previous_operation_manufactured_qty(row, 10)
		self.assertIn("process loss", str(loss_error.exception))

		row.process_loss_qty = 0
		with self.assertRaises(OperationSequenceError) as pending_error:
			jc.validate_previous_operation_manufactured_qty(row, 10)
		self.assertIn("Submit the manufacturing entry", str(pending_error.exception))

		jc.validate_previous_operation_manufactured_qty(row, 8)

	def test_semi_fg_job_card_is_exempt_from_transfer_qty_check(self):
		jc = frappe.new_doc("Job Card")
		jc.track_semi_finished_goods = 1
		jc.skip_material_transfer = 1
		jc.for_quantity = 10
		jc.transferred_qty = 0
		jc.append("items", {"item_code": "_Test Item"})

		jc.validate_transfer_qty()

		# with transfer enabled, a legacy card without an FG item keeps the strict check
		jc.skip_material_transfer = 0
		self.assertRaises(frappe.ValidationError, jc.validate_transfer_qty)

		jc.finished_good = "_Test Item"
		jc.validate_transfer_qty()

		jc.finished_good = None
		jc.track_semi_finished_goods = 0
		self.assertRaises(frappe.ValidationError, jc.validate_transfer_qty)
