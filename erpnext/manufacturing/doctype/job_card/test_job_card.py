# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


from typing import Literal

import frappe
from frappe.test_runner import make_test_records
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import flt, random_string
from frappe.utils.data import add_to_date, now, today

from erpnext.manufacturing.doctype.job_card.job_card import (
	JobCardCancelError,
	JobCardOverTransferError,
	OperationMismatchError,
	OperationSequenceError,
	OverlapError,
	make_corrective_job_card,
	make_material_request,
)
from erpnext.manufacturing.doctype.job_card.job_card import (
	make_stock_entry as make_stock_entry_from_jc,
)
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.doctype.work_order.work_order import WorkOrder, make_job_card
from erpnext.manufacturing.doctype.work_order.work_order import (
	make_stock_entry as make_stock_entry_for_work_order,
)
from erpnext.manufacturing.doctype.workstation.test_workstation import make_workstation
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.stock_entry.stock_entry import OperationsNotCompleteError
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry


class TestJobCard(FrappeTestCase):
	def setUp(self):
		make_bom_for_jc_tests()
		self.transfer_material_against: Literal["Work Order", "Job Card"] = "Work Order"
		self.source_warehouse = None
		self._work_order = None

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

	def tearDown(self):
		frappe.db.rollback()

	def test_job_card_operations(self):
		job_cards = frappe.get_all(
			"Job Card", filters={"work_order": self.work_order.name}, fields=["operation_id", "name"]
		)

		if job_cards:
			job_card = job_cards[0]
			frappe.db.set_value("Job Card", job_card.name, "operation_row_number", job_card.operation_id)

			doc = frappe.get_doc("Job Card", job_card.name)
			doc.operation_id = "Test Data"
			self.assertRaises(OperationMismatchError, doc.save)

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

	def test_removing_all_time_logs_clears_actual_dates(self):
		job_card = frappe.get_last_doc("Job Card", {"work_order": self.work_order.name})
		job_card.append("time_logs", {"from_time": "2024-03-01 08:00:00", "to_time": "2024-03-01 09:00:00"})
		job_card.save()
		self.assertTrue(job_card.actual_start_date and job_card.actual_end_date)

		job_card.set("time_logs", [])
		job_card.save()
		self.assertEqual((job_card.actual_start_date, job_card.actual_end_date), (None, None))

	def test_job_card_overlap(self):
		wo2 = make_wo_order_test_record(item="_Test FG Item 2", qty=2)

		jc1 = frappe.get_last_doc("Job Card", {"work_order": self.work_order.name})
		jc2 = frappe.get_last_doc("Job Card", {"work_order": wo2.name})

		employee = "_T-Employee-00001"  # from test records

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
		self.assertEqual(len(transfer_entry_2.items), 1)
		transfer_entry_2.insert()
		transfer_entry_2.submit()

		# 'For Quantity' here will be 0 since
		# transfer was made for 2 fg qty in first transfer Stock Entry
		self.assertEqual(transfer_entry_2.fg_completed_qty, 0)

	@change_settings("Manufacturing Settings", {"job_card_excess_transfer": 1})
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

	def test_job_card_time_log_blocked_until_material_transfer(self):
		"Time logs must wait for the transfer when RMs move against Job Card."
		self.transfer_material_against = "Job Card"
		self.source_warehouse = "Stores - _TC"

		self.generate_required_stock(self.work_order)
		job_card = frappe.get_last_doc("Job Card", {"work_order": self.work_order.name})

		self.assertRaises(
			frappe.ValidationError, job_card.add_time_log, frappe._dict(start_time=now(), employees=[])
		)

		transfer_entry = make_stock_entry_from_jc(job_card.name)
		transfer_entry.insert()
		transfer_entry.submit()

		job_card.reload()
		job_card.add_time_log(frappe._dict(start_time=now(), employees=[]))
		self.assertTrue(job_card.time_logs)

	@change_settings("Manufacturing Settings", {"job_card_excess_transfer": 0})
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
		transfer_entry_2 = frappe.copy_doc(transfer_entry_1)
		# deliberately change 'For Quantity'
		transfer_entry_2.fg_completed_qty = 1
		transfer_entry_2.items[0].qty = 5
		transfer_entry_2.items[1].qty = 3

		def save_and_submit():
			transfer_entry_2.insert()
			transfer_entry_2.submit()

		self.assertRaises(JobCardOverTransferError, save_and_submit)

	@change_settings("Manufacturing Settings", {"job_card_excess_transfer": 0})
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

	@change_settings(
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

	@change_settings(
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

		from erpnext.manufacturing.doctype.work_order.work_order import (
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
		workstation = job_card.workstation
		job_card = frappe.get_last_doc("Job Card", {"work_order": wo.name})
		job_card.update({"for_quantity": 3})
		job_card.workstation = workstation
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
		from erpnext.stock.doctype.material_request.material_request import make_stock_entry

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

	def test_job_card_proccess_qty_and_completed_qty(self):
		from erpnext.manufacturing.doctype.routing.test_routing import (
			create_routing,
			setup_bom,
			setup_operations,
		)
		from erpnext.manufacturing.doctype.work_order.work_order import (
			make_stock_entry as make_stock_entry_for_wo,
		)
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		operations = [
			{"operation": "Test Operation A1", "workstation": "Test Workstation A", "time_in_mins": 30},
			{"operation": "Test Operation B1", "workstation": "Test Workstation A", "time_in_mins": 20},
		]

		make_test_records("UOM")

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
			from_wip_warehouse=1,
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
		jc2.for_quantity = 8
		jc2.save()
		jc2.submit()

		self.assertEqual(jc2.for_quantity, 8)
		self.assertEqual(jc2.process_loss_qty, 0)

		s = frappe.get_doc(make_stock_entry_for_wo(wo_doc.name, "Manufacture", 10))
		s.submit()

		self.assertEqual(s.process_loss_qty, 2)

		wo_doc.reload()
		self.assertEqual([row.completed_qty for row in wo_doc.operations], [8, 8])
		self.assertEqual([row.process_loss_qty for row in wo_doc.operations], [2, 0])

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

	def test_upstream_process_loss_in_manufacturing(self):
		for upstream_qty, upstream_output, downstream_qty, downstream_output, manufacture_entries in (
			(100, 95, 95, 95, [(100, 5, 95)]),
			(100, 95, 95, 90, [(50, 10, 40), (50, 0, 50)]),
			(50, 45, 45, 45, [(50, 5, 45)]),
		):
			with self.subTest(
				upstream_qty=upstream_qty, downstream_qty=downstream_qty, output=downstream_output
			):
				work_order = self.make_two_operation_work_order(qty=100)
				job_cards = frappe.get_all(
					"Job Card", filters={"work_order": work_order.name}, order_by="sequence_id", pluck="name"
				)
				for index, (for_quantity, completed_qty) in enumerate(
					((upstream_qty, upstream_output), (downstream_qty, downstream_output))
				):
					job_card = frappe.get_doc("Job Card", job_cards[index])
					job_card.for_quantity = for_quantity
					job_card.append(
						"time_logs",
						{
							"from_time": add_to_date("2024-03-01 08:00:00", hours=index),
							"to_time": add_to_date("2024-03-01 08:00:00", hours=index, minutes=30),
							"completed_qty": completed_qty,
						},
					)
					job_card.save()
					job_card.submit()

				work_order.reload()
				self.assertEqual(
					[row.status for row in work_order.operations],
					["Completed" if upstream_qty == 100 else "Work in Progress"] * 2,
				)
				if upstream_qty == 100:
					# Simulate the stored operation status of an existing work order after upgrading.
					work_order.operations[1].db_set("status", "Work in Progress")
					work_order = frappe.get_doc("Work Order", work_order.name)
					work_order.run_method("onload")
					work_order.expected_delivery_date = add_to_date(today(), days=1)
					work_order.save()
					self.assertEqual(
						str(work_order.reload().expected_delivery_date), add_to_date(today(), days=1)
					)
					self.assertEqual(work_order.operations[1].status, "Work in Progress")

				frappe.get_doc("BOM", work_order.bom_no).db_set("process_loss_percentage", 10)
				entries = []
				for qty, loss, finished_qty in manufacture_entries:
					stock_entry = frappe.get_doc(
						make_stock_entry_for_work_order(work_order.name, "Manufacture", qty)
					)
					stock_entry.submit()
					self.assertEqual(stock_entry.process_loss_qty, loss)
					self.assertEqual(
						sum(row.qty for row in stock_entry.items if row.is_finished_item), finished_qty
					)
					ledger = frappe.db.get_value(
						"Stock Ledger Entry",
						{
							"voucher_no": stock_entry.name,
							"item_code": work_order.production_item,
							"is_cancelled": 0,
						},
						["actual_qty", "stock_value_difference"],
						as_dict=True,
					)
					self.assertEqual(ledger.actual_qty, finished_qty)
					self.assertEqual(ledger.stock_value_difference, qty * 200)
					entries.append(stock_entry)

				if upstream_qty < 100:
					# v16 checks the operations while it fetches the items
					with self.assertRaises(OperationsNotCompleteError):
						frappe.get_doc(
							make_stock_entry_for_work_order(work_order.name, "Manufacture", 5)
						).submit()
				else:
					self.assertEqual(work_order.reload().status, "Completed")

				work_order.reload()
				self.assertEqual(work_order.produced_qty, downstream_output)
				self.assertEqual(work_order.process_loss_qty, sum(row[1] for row in manufacture_entries))
				self.assertEqual(
					frappe.db.count("Stock Entry", {"work_order": work_order.name, "docstatus": 1}),
					len(entries),
				)
				for entry in reversed(entries):
					entry.cancel()
				self.assertEqual(work_order.reload().produced_qty, 0)
				self.assertEqual(work_order.process_loss_qty, 0)
				for name in reversed(job_cards):
					frappe.get_doc("Job Card", name).cancel()
				self.assertTrue(all(row.status == "Pending" for row in work_order.reload().operations))

	def test_job_card_input_limited_to_previous_operation_output(self):
		work_order = self.make_two_operation_work_order(qty=100)
		first, second = (
			frappe.get_doc("Job Card", name)
			for name in frappe.get_all(
				"Job Card", filters={"work_order": work_order.name}, order_by="sequence_id", pluck="name"
			)
		)
		for index, job_card in enumerate((first, second)):
			job_card.append(
				"time_logs",
				{
					"from_time": add_to_date("2024-04-10 08:00:00", hours=index),
					"to_time": add_to_date("2024-04-10 08:00:00", hours=index, minutes=30),
					"completed_qty": 95,
				},
			)
			job_card.save()
			if job_card is first:
				job_card.submit()

		self.assertEqual(second.process_loss_qty, 5)
		self.assertRaises(OperationSequenceError, second.submit)

		second.reload()
		second.for_quantity = 95
		second.time_logs[0].completed_qty = 90
		second.save()
		second.submit()
		self.assertEqual(second.process_loss_qty, 5)

		# A later card without loss can't use the qty already lost.
		make_job_card(
			work_order.name,
			[
				{
					"name": second.operation_id,
					"operation": second.operation,
					"sequence_id": second.sequence_id,
					"qty": 5,
					"pending_qty": 5,
				}
			],
		)
		extra = frappe.get_last_doc("Job Card", {"work_order": work_order.name})
		extra.append(
			"time_logs",
			{
				"from_time": "2024-04-10 10:00:00",
				"to_time": "2024-04-10 10:30:00",
				"completed_qty": 5,
			},
		)
		self.assertRaises(OperationSequenceError, extra.submit)

	def test_upstream_cancel_counts_process_loss_of_later_operation(self):
		work_order = self.make_two_operation_work_order(qty=10)
		first, second = (
			frappe.get_doc("Job Card", name)
			for name in frappe.get_all(
				"Job Card", filters={"work_order": work_order.name}, order_by="sequence_id", pluck="name"
			)
		)
		make_job_card(
			work_order.name,
			[
				{
					"name": first.operation_id,
					"operation": first.operation,
					"sequence_id": first.sequence_id,
					"qty": 2,
					"pending_qty": 2,
				}
			],
		)
		extra = frappe.get_last_doc("Job Card", {"work_order": work_order.name})
		first.for_quantity = 8

		for index, (job_card, completed_qty) in enumerate(((first, 8), (extra, 2), (second, 8))):
			job_card.append(
				"time_logs",
				{
					"from_time": add_to_date("2024-04-10 08:00:00", hours=index),
					"to_time": add_to_date("2024-04-10 08:00:00", hours=index, minutes=30),
					"completed_qty": completed_qty,
				},
			)
			job_card.save()
			job_card.submit()

		self.assertEqual(second.process_loss_qty, 2)
		self.assertRaises(OperationSequenceError, extra.cancel)

	def test_op_cost_calculation(self):
		from erpnext.manufacturing.doctype.routing.test_routing import (
			create_routing,
			setup_bom,
			setup_operations,
		)
		from erpnext.manufacturing.doctype.work_order.work_order import make_job_card
		from erpnext.manufacturing.doctype.work_order.work_order import (
			make_stock_entry as make_stock_entry_for_wo,
		)
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		suffix = random_string(5)
		workstation = make_workstation(
			workstation_name=f"Test Workstation Z {suffix}", hour_rate_rent=240, hour_rate_labour=0
		)
		workstation.update(
			{
				"hour_rate_rent": 240,
				"hour_rate_labour": 0,
				"hour_rate_electricity": 0,
				"hour_rate_consumable": 0,
			}
		)
		workstation.save()
		operations = [
			{
				"operation": f"Test Operation A1 {suffix}",
				"workstation": workstation.name,
				"time_in_mins": 30,
			},
		]

		warehouse = create_warehouse(f"Test Warehouse 123 for Job Card {suffix}")
		setup_operations(operations)

		item_code = f"Test Job Card Process Qty Item {suffix}"
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
		from_time = "2025-01-01 09:00:00"
		for _ in jc.scheduled_time_logs:
			jc.append(
				"time_logs",
				{
					"from_time": from_time,
					"to_time": add_to_date(from_time, minutes=1),
					"completed_qty": 4,
				},
			)
		jc.for_quantity = 4
		jc.save()
		jc.submit()

		s1 = frappe.get_doc(make_stock_entry_for_wo(wo_doc.name, "Manufacture", 4))
		s1.submit()

		wo_doc.reload()
		precision = s1.additional_costs[0].precision("amount")
		self.assertEqual(
			flt(s1.additional_costs[0].amount, precision),
			flt(wo_doc.operations[0].actual_operating_cost, precision),
		)

		make_job_card(
			wo_doc.name,
			[
				{
					"name": wo_doc.operations[0].name,
					"operation": operations[0]["operation"],
					"workstation": wo_doc.operations[0].workstation,
					"qty": 6,
					"pending_qty": 6,
				}
			],
		)

		job_card = frappe.get_last_doc("Job Card", {"work_order": wo_doc.name})
		from_time = "2025-01-01 10:00:00"
		job_card.append(
			"time_logs",
			{
				"from_time": from_time,
				"to_time": add_to_date(from_time, minutes=2),
				"completed_qty": 6,
			},
		)
		job_card.for_quantity = 6
		job_card.save()
		job_card.submit()

		s2 = frappe.get_doc(make_stock_entry_for_wo(wo_doc.name, "Manufacture", 6))
		wo_doc.reload()
		precision = s2.additional_costs[0].precision("amount")
		self.assertEqual(
			flt(s2.additional_costs[0].amount, precision),
			flt(wo_doc.operations[0].actual_operating_cost - s1.additional_costs[0].amount, precision),
		)

	@change_settings("Manufacturing Settings", {"overproduction_percentage_for_work_order": 100})
	def test_operating_cost_with_overproduction(self):
		from erpnext.manufacturing.doctype.routing.test_routing import (
			create_routing,
			setup_bom,
			setup_operations,
		)
		from erpnext.manufacturing.doctype.work_order.work_order import make_job_card
		from erpnext.manufacturing.doctype.work_order.work_order import (
			make_stock_entry as make_stock_entry_for_wo,
		)
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		suffix = random_string(5)
		workstation = make_workstation(
			workstation_name=f"Test Workstation for Overproduction {suffix}",
			hour_rate_rent=10,
			hour_rate_labour=10,
		)
		workstation.update(
			{
				"hour_rate_rent": 10,
				"hour_rate_labour": 10,
				"hour_rate_electricity": 0,
				"hour_rate_consumable": 0,
			}
		)
		workstation.save()
		operations = [
			{"operation": f"Test Operation 1 {suffix}", "workstation": workstation.name, "time_in_mins": 30},
			{"operation": f"Test Operation 2 {suffix}", "workstation": workstation.name, "time_in_mins": 30},
		]
		warehouse = create_warehouse(f"Test Warehouse for Overproduction {suffix}")
		setup_operations(operations)

		fg = make_item(f"Test FG for Overproduction {suffix}", {"stock_uom": "Nos", "is_stock_item": 1})
		rm = make_item(f"Test RM for Overproduction {suffix}", {"stock_uom": "Nos", "is_stock_item": 1})

		routing_doc = create_routing(routing_name=f"Testing Route {suffix}", operations=operations)
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
		from_time = "2025-01-02 09:00:00"
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
		from_time = "2025-01-05 09:00:00"
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

		def assert_operating_costs(stock_entry, qty, previous_entries):
			wo_doc.reload()
			for idx, operation in enumerate(wo_doc.operations):
				consumed_cost = sum(
					entry.additional_costs[idx].amount for entry in previous_entries if entry.docstatus == 1
				)
				consumed_qty = sum(
					entry.additional_costs[idx].qty for entry in previous_entries if entry.docstatus == 1
				)
				remaining_cost = operation.actual_operating_cost - consumed_cost
				remaining_qty = operation.completed_qty - consumed_qty
				precision = stock_entry.additional_costs[idx].precision("amount")
				expected_cost = flt(remaining_cost / remaining_qty * min(remaining_qty, qty), precision)

				self.assertEqual(flt(stock_entry.additional_costs[idx].amount, precision), expected_cost)

		assert_operating_costs(s, 6, [])

		make_job_card(
			wo_doc.name,
			[
				{
					"name": wo_doc.operations[0].name,
					"operation": operations[0]["operation"],
					"workstation": wo_doc.operations[0].workstation,
					"qty": 2,
					"pending_qty": 2,
				}
			],
		)

		job_card = frappe.get_last_doc("Job Card", {"work_order": wo_doc.name})
		from_time = "2025-01-09 09:00:00"
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
					"operation": operations[1]["operation"],
					"workstation": wo_doc.operations[1].workstation,
					"qty": 2,
					"pending_qty": 2,
				}
			],
		)

		job_card = frappe.get_last_doc("Job Card", {"work_order": wo_doc.name})
		from_time = "2025-01-12 09:00:00"
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

		assert_operating_costs(s2, 1, [s])

		make_job_card(
			wo_doc.name,
			[
				{
					"name": wo_doc.operations[0].name,
					"operation": operations[0]["operation"],
					"workstation": wo_doc.operations[0].workstation,
					"qty": 2,
					"pending_qty": 2,
				}
			],
		)

		job_card = frappe.get_last_doc("Job Card", {"work_order": wo_doc.name})
		from_time = "2025-01-16 09:00:00"
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
					"operation": operations[1]["operation"],
					"workstation": wo_doc.operations[1].workstation,
					"qty": 2,
					"pending_qty": 2,
				}
			],
		)

		job_card = frappe.get_last_doc("Job Card", {"work_order": wo_doc.name})
		from_time = "2025-01-19 09:00:00"
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

		s3 = frappe.get_doc(make_stock_entry_for_wo(wo_doc.name, "Manufacture", 2))
		s3.submit()

		assert_operating_costs(s3, 2, [s, s2])

		s2.cancel()

		s4 = frappe.get_doc(make_stock_entry_for_wo(wo_doc.name, "Manufacture", 3))
		s4.submit()

		assert_operating_costs(s4, 3, [s, s3])

	def test_completed_qty_sums_without_float_noise(self):
		jc = frappe.new_doc("Job Card")
		jc.update({"docstatus": 1, "for_quantity": 0.8, "total_completed_qty": 0.7, "process_loss_qty": 0.1})
		jc.append("items", {"item_code": "_Test Item"})
		jc.set_status()
		self.assertEqual(jc.status, "Completed")

	def test_set_process_loss(self):
		nothing_done = frappe.new_doc("Job Card")
		nothing_done.for_quantity = 10
		nothing_done.total_completed_qty = 0
		nothing_done.set_process_loss()
		self.assertEqual(nothing_done.process_loss_qty, 0)

		all_process_loss = frappe.new_doc("Job Card")
		all_process_loss.for_quantity = 10
		all_process_loss.process_loss_qty = 10
		all_process_loss.set_process_loss()
		self.assertEqual(all_process_loss.process_loss_qty, 10)

	def test_lowered_overproduction_allowance_checks_only_job_card_operation(self):
		from erpnext.manufacturing.doctype.operation.test_operation import make_operation

		item = create_item("Lowered Allowance FG").name
		bom = frappe.new_doc("BOM", company="_Test Company", item=item, quantity=1, with_operations=1)
		bom.append("items", {"item_code": "_Test Item", "qty": 1})
		for operation in ("Lowered Allowance Op A", "Lowered Allowance Op B"):
			make_operation(operation=operation, workstation="_Test Workstation 1")
			bom.append(
				"operations",
				{"operation": operation, "workstation": "_Test Workstation 1", "time_in_mins": 1},
			)
		bom.insert()
		bom.submit()

		def complete(job_card, qty, hours):
			job_card.append(
				"time_logs",
				{
					"from_time": add_to_date(now(), hours=hours),
					"to_time": add_to_date(now(), hours=hours + 1),
					"completed_qty": qty,
				},
			)

		with change_settings("Manufacturing Settings", {"overproduction_percentage_for_work_order": 100}):
			work_order = make_wo_order_test_record(
				item=item, qty=2, bom_no=bom.name, skip_transfer=1, source_warehouse="Stores - _TC"
			)
			job_card_a = frappe.get_last_doc(
				"Job Card", {"work_order": work_order.name, "operation": "Lowered Allowance Op A"}
			)
			job_card_a.for_quantity = 4
			complete(job_card_a, 4, -4)
			job_card_a.submit()

		with change_settings("Manufacturing Settings", {"overproduction_percentage_for_work_order": 0}):
			job_card_b = frappe.get_last_doc(
				"Job Card", {"work_order": work_order.name, "operation": "Lowered Allowance Op B"}
			)
			complete(job_card_b, 2, -2)
			job_card_b.submit()

			operation_a = work_order.operations[0]
			make_job_card(
				work_order.name,
				[
					{
						"name": operation_a.name,
						"operation": operation_a.operation,
						"workstation": operation_a.workstation,
						"qty": 1,
						"pending_qty": 1,
					}
				],
			)
			extra_job_card_a = frappe.get_last_doc(
				"Job Card", {"operation_id": operation_a.name, "docstatus": 0}
			)
			complete(extra_job_card_a, 1, 5)
			self.assertRaisesRegex(
				frappe.ValidationError, "Completed Qty cannot be greater", extra_job_card_a.submit
			)

		work_order.reload()
		self.assertEqual([row.status for row in work_order.operations], ["Completed", "Completed"])

	@change_settings("Manufacturing Settings", {"disable_capacity_planning": 1})
	def test_sub_operations_with_two_operators_keep_completed_qty(self):
		workstation = make_jc_review_workstation()
		cutting = make_jc_review_operation(workstation)
		welding = make_jc_review_operation(workstation)
		operation = make_jc_review_operation(
			workstation, sub_operations=[{"operation": cutting}, {"operation": welding}]
		)
		rm_item = make_jc_review_item()
		wo = make_jc_review_work_order(
			make_jc_review_item(),
			[{"item_code": rm_item, "qty": 1}],
			[{"operation": operation, "workstation": workstation, "time_in_mins": 60}],
		)
		first_operator, second_operator = make_jc_review_employee(), make_jc_review_employee()

		job_card = get_jc_review_job_cards(wo.name)[0]
		for idx, (sub_operation, completed_qty) in enumerate(((cutting, 0), (welding, 10))):
			start = add_to_date("2031-03-03 08:00:00", hours=idx)
			job_card.append("time_logs", jc_review_log(start, 30, 0, first_operator, operation=sub_operation))
			job_card.append(
				"time_logs",
				jc_review_log(start, 30, completed_qty, second_operator, operation=sub_operation),
			)
		job_card.save()
		job_card.save()

		self.assertEqual([row.completed_qty for row in job_card.sub_operations], [0, 10])
		self.assertEqual((job_card.total_completed_qty, job_card.process_loss_qty), (10, 0))

	@change_settings("Manufacturing Settings", {"disable_capacity_planning": 1})
	def test_operation_cost_uses_each_job_card_workstation_rate(self):
		first_workstation = make_jc_review_workstation(hour_rate=600)
		second_workstation = make_jc_review_workstation(hour_rate=1200)
		operation = make_jc_review_operation(first_workstation)
		wo = make_jc_review_work_order(
			make_jc_review_item(),
			[{"item_code": make_jc_review_item(), "qty": 1}],
			[{"operation": operation, "workstation": first_workstation, "time_in_mins": 60}],
			skip_transfer=1,
		)

		first_card = get_jc_review_job_cards(wo.name)[0]
		second_card = frappe.copy_doc(first_card)
		first_card.for_quantity = 5
		first_card.append("time_logs", jc_review_log("2031-03-03 08:00:00", 60, 5))
		first_card.submit()

		second_card.update({"workstation": second_workstation, "for_quantity": 5})
		second_card.set("time_logs", [jc_review_log("2031-03-03 10:00:00", 60, 5)])
		second_card.set("scheduled_time_logs", [])
		second_card.insert()
		second_card.submit()

		operation_cost = frappe.db.get_value(
			"Work Order Operation", {"parent": wo.name}, "actual_operating_cost"
		)
		self.assertEqual(operation_cost, 1800)

		second_card.cancel()
		operation_cost = frappe.db.get_value(
			"Work Order Operation", {"parent": wo.name}, "actual_operating_cost"
		)
		self.assertEqual(operation_cost, 600)

	@change_settings("Manufacturing Settings", {"disable_capacity_planning": 1})
	def test_workstation_capacity_counts_logs_of_other_employees(self):
		workstation = make_jc_review_workstation(capacity=1)
		operation = make_jc_review_operation(workstation)
		operations = [{"operation": operation, "workstation": workstation, "time_in_mins": 60}]
		rows = [{"item_code": make_jc_review_item(), "qty": 1}]
		fg_item = make_jc_review_item()
		first_card = get_jc_review_job_cards(
			make_jc_review_work_order(fg_item, rows, operations, skip_transfer=1).name
		)[0]
		second_card = get_jc_review_job_cards(
			make_jc_review_work_order(fg_item, rows, operations, skip_transfer=1).name
		)[0]

		first_card.append(
			"time_logs", jc_review_log("2031-03-03 17:20:00", 60, 10, make_jc_review_employee())
		)
		first_card.submit()

		second_card.append(
			"time_logs", jc_review_log("2031-03-03 17:50:00", 60, 10, make_jc_review_employee())
		)
		self.assertRaises(OverlapError, second_card.save)

	@change_settings("Manufacturing Settings", {"disable_capacity_planning": 1})
	def test_two_operators_on_one_card_take_one_workstation_slot(self):
		workstation = make_jc_review_workstation(capacity=2)
		operation = make_jc_review_operation(workstation)
		operations = [{"operation": operation, "workstation": workstation, "time_in_mins": 60}]
		rows = [{"item_code": make_jc_review_item(), "qty": 1}]
		fg_item = make_jc_review_item()
		first_card = get_jc_review_job_cards(
			make_jc_review_work_order(fg_item, rows, operations, skip_transfer=1).name
		)[0]
		second_card = get_jc_review_job_cards(
			make_jc_review_work_order(fg_item, rows, operations, skip_transfer=1).name
		)[0]

		first_card.append("time_logs", jc_review_log("2031-03-15 08:00:00", 60, 0, make_jc_review_employee()))
		first_card.append(
			"time_logs", jc_review_log("2031-03-15 08:00:00", 60, 10, make_jc_review_employee())
		)
		first_card.submit()

		second_card.append(
			"time_logs", jc_review_log("2031-03-15 08:00:00", 60, 10, make_jc_review_employee())
		)
		second_card.save()
		self.assertEqual(len(second_card.time_logs), 1)

	@change_settings("Manufacturing Settings", {"disable_capacity_planning": 1})
	def test_employee_cannot_log_overlapping_time_anywhere(self):
		rows = [{"item_code": make_jc_review_item(), "qty": 1}]
		fg_item = make_jc_review_item()
		job_cards = []
		for _idx in range(2):
			workstation = make_jc_review_workstation(capacity=2)
			operation = make_jc_review_operation(workstation)
			operations = [{"operation": operation, "workstation": workstation, "time_in_mins": 60}]
			wo = make_jc_review_work_order(fg_item, rows, operations, skip_transfer=1)
			job_cards.append(get_jc_review_job_cards(wo.name)[0])

		employee = make_jc_review_employee()
		first_card, second_card = job_cards
		first_card.append("time_logs", jc_review_log("2031-03-04 08:00:00", 60, 10, employee))
		first_card.save()

		second_card.append("time_logs", jc_review_log("2031-03-04 08:30:00", 60, 10, employee))
		self.assertRaisesRegex(OverlapError, "is already working", second_card.save)

		first_card.append("time_logs", jc_review_log("2031-03-04 08:00:00", 60, 0, employee))
		self.assertRaisesRegex(OverlapError, "is already working", first_card.save)

	@change_settings("Manufacturing Settings", {"disable_capacity_planning": 1})
	def test_employee_overlap_hides_a_job_card_the_user_cannot_read(self):
		from frappe.permissions import add_user_permission

		rows = [{"item_code": make_jc_review_item(), "qty": 1}]
		fg_item = make_jc_review_item()
		cards = []
		for _idx in range(2):
			workstation = make_jc_review_workstation()
			operation = make_jc_review_operation(workstation)
			operations = [{"operation": operation, "workstation": workstation, "time_in_mins": 60}]
			wo = make_jc_review_work_order(fg_item, rows, operations, skip_transfer=1)
			cards.append(get_jc_review_job_cards(wo.name)[0])

		allowed_card, restricted_card = cards
		employee = make_jc_review_employee()
		restricted_card.append("time_logs", jc_review_log("2031-03-16 08:00:00", 60, 0, employee))
		restricted_card.save()

		user = make_jc_review_user("jc-overlap-restricted@example.com")
		add_user_permission("Work Order", allowed_card.work_order, user.name)
		with self.set_user(user.name):
			card = frappe.get_doc("Job Card", allowed_card.name)
			card.append("time_logs", jc_review_log("2031-03-16 08:30:00", 60, 0, employee))
			with self.assertRaises(OverlapError) as error:
				card.save()

		self.assertNotIn(restricted_card.name, str(error.exception))

	@change_settings("Manufacturing Settings", {"disable_capacity_planning": 1})
	def test_employee_with_an_earlier_draft_card_can_log_on_a_shared_workstation(self):
		shared_workstation = make_jc_review_workstation(capacity=2)
		other_workstation = make_jc_review_workstation()
		shared_operation = make_jc_review_operation(shared_workstation)
		other_operation = make_jc_review_operation(other_workstation)
		employee, colleague = make_jc_review_employee(), make_jc_review_employee()

		def make_card(operation, workstation):
			wo = make_jc_review_work_order(
				make_jc_review_item(),
				[{"item_code": make_jc_review_item(), "qty": 1}],
				[{"operation": operation, "workstation": workstation, "time_in_mins": 60}],
			)
			return get_jc_review_job_cards(wo.name)[0]

		earlier_card = make_card(other_operation, other_workstation)
		earlier_card.append("time_logs", jc_review_log("2031-04-01 08:00:00", 60, 0, employee))
		earlier_card.save()
		colleague_card = make_card(shared_operation, shared_workstation)
		colleague_card.append("time_logs", jc_review_log("2031-04-01 10:00:00", 60, 0, colleague))
		colleague_card.save()

		job_card = make_card(shared_operation, shared_workstation)
		job_card.append("time_logs", jc_review_log("2031-04-01 10:30:00", 60, 0, employee))
		job_card.save()

		self.assertEqual(len(job_card.time_logs), 1)

	@change_settings("Manufacturing Settings", {"disable_capacity_planning": 1})
	def test_two_operators_on_one_job_charge_the_workstation_once(self):
		workstation = make_jc_review_workstation(hour_rate=600, capacity=1)
		operation = make_jc_review_operation(workstation)
		wo = make_jc_review_work_order(
			make_jc_review_item(),
			[{"item_code": make_jc_review_item(), "qty": 1}],
			[{"operation": operation, "workstation": workstation, "time_in_mins": 60}],
			skip_transfer=1,
		)

		job_card = get_jc_review_job_cards(wo.name)[0]
		job_card.append("time_logs", jc_review_log("2031-03-05 08:00:00", 60, 0, make_jc_review_employee()))
		job_card.append("time_logs", jc_review_log("2031-03-05 08:00:00", 60, 10, make_jc_review_employee()))
		job_card.submit()

		self.assertEqual(job_card.total_time_in_mins, 60)
		operation_row = frappe.db.get_value(
			"Work Order Operation",
			{"parent": wo.name},
			["actual_operation_time", "actual_operating_cost"],
			as_dict=True,
		)
		self.assertEqual(
			(operation_row.actual_operation_time, operation_row.actual_operating_cost), (60, 600)
		)

	@change_settings("Manufacturing Settings", {"disable_capacity_planning": 1})
	def test_job_card_with_materials_partly_transferred_cannot_be_submitted(self):
		workstation = make_jc_review_workstation()
		operation = make_jc_review_operation(workstation)
		first_item, second_item = make_jc_review_item(), make_jc_review_item()
		for item_code in (first_item, second_item):
			make_stock_entry(item_code=item_code, target="_Test Warehouse - _TC", qty=50, basic_rate=100)

		wo = make_jc_review_work_order(
			make_jc_review_item(),
			[
				{"item_code": first_item, "qty": 2, "operation": operation},
				{"item_code": second_item, "qty": 3, "operation": operation},
			],
			[{"operation": operation, "workstation": workstation, "time_in_mins": 60}],
			transfer_material_against="Job Card",
		)
		job_card = get_jc_review_job_cards(wo.name)[0]

		transfer = make_stock_entry_from_jc(job_card.name)
		transfer.items = [row for row in transfer.items if row.item_code == first_item]
		transfer.submit()

		job_card.reload()
		job_card.append("time_logs", jc_review_log("2031-03-07 08:00:00", 60, 10))
		self.assertRaisesRegex(frappe.ValidationError, "Materials needs to be transferred", job_card.submit)

	@change_settings("Manufacturing Settings", {"disable_capacity_planning": 1})
	def test_earlier_operation_cannot_be_undone_after_the_next_one(self):
		workstation = make_jc_review_workstation()
		cutting = make_jc_review_operation(workstation)
		welding = make_jc_review_operation(workstation)
		wo = make_jc_review_work_order(
			make_jc_review_item(),
			[{"item_code": make_jc_review_item(), "qty": 1}],
			[
				{"operation": cutting, "workstation": workstation, "time_in_mins": 60},
				{"operation": welding, "workstation": workstation, "time_in_mins": 60},
			],
			skip_transfer=1,
		)

		first_card, second_card = get_jc_review_job_cards(wo.name)
		first_card.append("time_logs", jc_review_log("2031-03-08 08:00:00", 60, 10))
		first_card.submit()
		second_card.append("time_logs", jc_review_log("2031-03-08 10:00:00", 60, 10))
		second_card.submit()

		self.assertRaises(OperationSequenceError, first_card.cancel)

	@change_settings("Manufacturing Settings", {"disable_capacity_planning": 1})
	def test_earlier_operation_after_manufacture_asks_to_cancel_the_manufacture_entry(self):
		workstation = make_jc_review_workstation()
		cutting = make_jc_review_operation(workstation)
		welding = make_jc_review_operation(workstation)
		raw_material = make_jc_review_item()
		make_stock_entry(item_code=raw_material, target="_Test Warehouse - _TC", qty=1, basic_rate=100)
		wo = make_jc_review_work_order(
			make_jc_review_item(),
			[{"item_code": raw_material, "qty": 1}],
			[
				{"operation": cutting, "workstation": workstation, "time_in_mins": 60},
				{"operation": welding, "workstation": workstation, "time_in_mins": 60},
			],
			qty=1,
			skip_transfer=1,
		)

		first_card, second_card = get_jc_review_job_cards(wo.name)
		first_card.append("time_logs", jc_review_log("2031-03-09 08:00:00", 60, 1))
		first_card.submit()
		second_card.append("time_logs", jc_review_log("2031-03-09 10:00:00", 60, 1))
		second_card.submit()
		frappe.get_doc(make_stock_entry_for_work_order(wo.name, "Manufacture", 1)).submit()

		self.assertRaises(JobCardCancelError, first_card.cancel)
		self.assertRaises(JobCardCancelError, second_card.cancel)

	@change_settings("Manufacturing Settings", {"disable_capacity_planning": 1})
	def test_job_card_lookups_follow_work_order_user_permissions(self):
		from frappe.permissions import add_user_permission

		from erpnext.manufacturing.doctype.job_card.job_card import get_job_details, get_operation_details

		workstation = make_jc_review_workstation()
		operation = make_jc_review_operation(workstation)
		rows = [{"item_code": make_jc_review_item(), "qty": 1}]
		operations = [{"operation": operation, "workstation": workstation, "time_in_mins": 60}]
		fg_item = make_jc_review_item()
		allowed = make_jc_review_work_order(fg_item, rows, operations, skip_transfer=1)
		restricted = make_jc_review_work_order(fg_item, rows, operations, skip_transfer=1)
		restricted_card = get_jc_review_job_cards(restricted.name)[0]
		restricted_card.append("time_logs", jc_review_log("2031-03-10 08:00:00", 60, 0))
		restricted_card.save()

		user = make_jc_review_user("jc-lookup-restricted@example.com")
		add_user_permission("Work Order", allowed.name, user.name)

		with self.set_user(user.name):
			self.assertEqual(
				get_job_details("2031-03-10", "2031-03-11", frappe.as_json({"work_order": restricted.name})),
				[],
			)
			self.assertRaises(frappe.PermissionError, get_operation_details, restricted.name, operation)
			self.assertEqual(len(get_operation_details(allowed.name, operation)), 1)

	@change_settings("Manufacturing Settings", {"disable_capacity_planning": 1})
	def test_second_material_transfer_maps_only_pending_rows(self):
		workstation = make_jc_review_workstation()
		operation = make_jc_review_operation(workstation)
		first_item, second_item = make_jc_review_item(), make_jc_review_item()
		for item_code in (first_item, second_item):
			make_stock_entry(item_code=item_code, target="_Test Warehouse - _TC", qty=50, basic_rate=100)

		wo = make_jc_review_work_order(
			make_jc_review_item(),
			[
				{"item_code": first_item, "qty": 2, "operation": operation},
				{"item_code": second_item, "qty": 3, "operation": operation},
			],
			[{"operation": operation, "workstation": workstation, "time_in_mins": 60}],
			transfer_material_against="Job Card",
		)
		job_card = get_jc_review_job_cards(wo.name)[0]

		transfer = make_stock_entry_from_jc(job_card.name)
		transfer.items = [row for row in transfer.items if row.item_code == first_item]
		transfer.submit()

		next_transfer = make_stock_entry_from_jc(job_card.name)
		self.assertEqual([(row.item_code, row.qty) for row in next_transfer.items], [(second_item, 30)])

	@change_settings("Manufacturing Settings", {"disable_capacity_planning": 1})
	def test_corrective_job_card_after_process_loss(self):
		workstation = make_jc_review_workstation()
		operation = make_jc_review_operation(workstation)
		rework = make_jc_review_operation(workstation)
		wo = make_jc_review_work_order(
			make_jc_review_item(),
			[{"item_code": make_jc_review_item(), "qty": 1}],
			[{"operation": operation, "workstation": workstation, "time_in_mins": 60}],
			skip_transfer=1,
		)
		job_card = get_jc_review_job_cards(wo.name)[0]
		job_card.append("time_logs", jc_review_log("2031-03-12 08:00:00", 60, 8))
		job_card.save()
		job_card.submit()
		self.assertEqual(job_card.process_loss_qty, 2)

		corrective = make_corrective_job_card(job_card.name, operation=rework, for_operation=operation)
		corrective.insert()
		self.assertEqual(corrective.process_loss_qty, 0)

	@change_settings("Manufacturing Settings", {"disable_capacity_planning": 1})
	def test_material_request_updates_job_card_requested_qty(self):
		workstation = make_jc_review_workstation()
		operation = make_jc_review_operation(workstation)
		rm_item = make_jc_review_item()
		wo = make_jc_review_work_order(
			make_jc_review_item(),
			[{"item_code": rm_item, "qty": 2, "operation": operation}],
			[{"operation": operation, "workstation": workstation, "time_in_mins": 60}],
			transfer_material_against="Job Card",
		)
		job_card = get_jc_review_job_cards(wo.name)[0]

		material_request = make_material_request(job_card.name)
		material_request.schedule_date = today()
		material_request.submit()
		self.assertEqual(frappe.db.get_value("Job Card", job_card.name, "requested_qty"), 10)

		material_request.cancel()
		self.assertEqual(frappe.db.get_value("Job Card", job_card.name, "requested_qty"), 0)


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


def make_bom_for_jc_tests():
	test_records = frappe.get_test_records("BOM")
	bom = frappe.copy_doc(test_records[2])
	bom.set_rate_of_sub_assembly_item_based_on_bom = 0
	bom.rm_cost_as_per = "Valuation Rate"
	bom.items[0].uom = "_Test UOM 1"
	bom.items[0].conversion_factor = 5
	bom.insert()


def make_jc_review_item(**properties):
	from erpnext.stock.doctype.item.test_item import make_item

	return make_item(properties={"is_stock_item": 1, "valuation_rate": 100, **properties}).name


def make_jc_review_workstation(hour_rate=600, capacity=1):
	workstation = make_workstation(
		workstation_name=f"_Test JC Review Workstation {frappe.generate_hash(length=6)}",
		hour_rate_rent=hour_rate,
	).name
	frappe.db.set_value("Workstation", workstation, "production_capacity", capacity)
	return workstation


def make_jc_review_operation(workstation, **values):
	from erpnext.manufacturing.doctype.operation.test_operation import make_operation

	operation = make_operation(
		operation=f"_Test JC Review Operation {frappe.generate_hash(length=6)}", workstation=workstation
	)
	if values:
		operation.update(values)
		operation.save()
	return operation.name


def make_jc_review_work_order(fg_item, rows, operations, qty=10, **kwargs):
	bom = frappe.get_doc(
		{
			"doctype": "BOM",
			"item": fg_item,
			"company": "_Test Company",
			"currency": "INR",
			"quantity": 1,
			"rm_cost_as_per": "Valuation Rate",
			"with_operations": 1,
			"items": rows,
			"operations": operations,
		}
	)
	bom.insert()
	bom.submit()

	wo = frappe.get_doc(
		{
			"doctype": "Work Order",
			"production_item": fg_item,
			"bom_no": bom.name,
			"qty": qty,
			"company": "_Test Company",
			"source_warehouse": "_Test Warehouse - _TC",
			"wip_warehouse": "_Test Warehouse 1 - _TC",
			"fg_warehouse": "_Test Warehouse 2 - _TC",
			"planned_start_date": now(),
			**kwargs,
		}
	)
	wo.get_items_and_operations_from_bom()
	wo.insert()
	wo.submit()
	return wo


def get_jc_review_job_cards(work_order):
	return [
		frappe.get_doc("Job Card", name)
		for name in frappe.get_all(
			"Job Card", filters={"work_order": work_order}, order_by="sequence_id, creation", pluck="name"
		)
	]


def jc_review_log(from_time, minutes, completed_qty=0, employee=None, **values):
	return {
		"from_time": from_time,
		"to_time": add_to_date(from_time, minutes=minutes),
		"time_in_mins": minutes,
		"completed_qty": completed_qty,
		"employee": employee,
		**values,
	}


def make_jc_review_user(email):
	user = frappe.new_doc("User")
	user.update({"email": email, "first_name": email.split("@")[0], "send_welcome_email": 0})
	user.append("roles", {"role": "Manufacturing User"})
	return user.insert()


def make_jc_review_employee():
	from erpnext.setup.doctype.employee.test_employee import make_employee

	return make_employee(f"jc-review-{frappe.generate_hash(length=8)}@example.com", company="_Test Company")
