# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


from typing import Literal

import frappe
from frappe.test_runner import make_test_records
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import random_string
from frappe.utils.data import add_to_date, now, today

from erpnext.manufacturing.doctype.job_card.job_card import (
	JobCardOverTransferError,
	OperationMismatchError,
	OverlapError,
	make_corrective_job_card,
	make_material_request,
)
from erpnext.manufacturing.doctype.job_card.job_card import (
	make_stock_entry as make_stock_entry_from_jc,
)
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.doctype.work_order.work_order import WorkOrder
from erpnext.manufacturing.doctype.workstation.test_workstation import make_workstation
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
		del transfer_entry_2.items[0]
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
		transfer_entry_2 = make_stock_entry_from_jc(job_card_name)
		# deliberately change 'For Quantity'
		transfer_entry_2.fg_completed_qty = 1
		transfer_entry_2.items[0].qty = 5
		transfer_entry_2.items[1].qty = 3
		transfer_entry_2.insert()
		self.assertRaises(JobCardOverTransferError, transfer_entry_2.submit)

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

	def test_job_card_statuses(self):
		def assertStatus(status):
			jc.set_status()
			self.assertEqual(jc.status, status)

		jc = frappe.new_doc("Job Card")
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
		jc2.time_logs[0].completed_qty = 10

		self.assertRaises(frappe.ValidationError, jc2.save)

		jc2.load_from_db()
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
