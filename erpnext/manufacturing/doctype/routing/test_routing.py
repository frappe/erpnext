# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase

from erpnext.manufacturing.doctype.job_card.job_card import OperationSequenceError
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.stock.doctype.item.test_item import make_item

EXTRA_TEST_RECORD_DEPENDENCIES = ["UOM"]


class UnitTestRouting(UnitTestCase):
	"""
	Unit tests for Routing.
	Use this class for testing individual functions and methods.
	"""

	pass


class TestRouting(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.item_code = "Test Routing Item - A"

	@classmethod
	def tearDownClass(cls):
		frappe.db.sql("delete from tabBOM where item=%s", cls.item_code)

	def test_sequence_id(self):
		operations = [
			{"operation": "Test Operation A", "workstation": "Test Workstation A", "time_in_mins": 30},
			{"operation": "Test Operation B", "workstation": "Test Workstation A", "time_in_mins": 20},
		]

		setup_operations(operations)
		routing_doc = create_routing(routing_name="Testing Route", operations=operations)
		bom_doc = setup_bom(item_code=self.item_code, routing=routing_doc.name)
		wo_doc = make_wo_order_test_record(production_item=self.item_code, bom_no=bom_doc.name)

		for row in routing_doc.operations:
			self.assertEqual(row.sequence_id, row.idx)

		for data in frappe.get_all(
			"Job Card", filters={"work_order": wo_doc.name}, order_by="sequence_id desc"
		):
			job_card_doc = frappe.get_doc("Job Card", data.name)
			for row in job_card_doc.scheduled_time_logs:
				job_card_doc.append(
					"time_logs",
					{
						"from_time": row.from_time,
						"to_time": row.to_time,
						"time_in_mins": row.time_in_mins,
					},
				)

			job_card_doc.time_logs[0].completed_qty = 10
			if job_card_doc.sequence_id != 1:
				self.assertRaises(OperationSequenceError, job_card_doc.save)
			else:
				job_card_doc.save()
				self.assertEqual(job_card_doc.total_completed_qty, 10)

		wo_doc.cancel()
		wo_doc.delete()

	def test_update_bom_operation_time(self):
		"""Update cost shouldn't update routing times."""
		operations = [
			{
				"operation": "Test Operation A",
				"workstation": "_Test Workstation A",
				"hour_rate_rent": 300,
				"hour_rate_labour": 750,
				"time_in_mins": 30,
			},
			{
				"operation": "Test Operation B",
				"workstation": "_Test Workstation B",
				"hour_rate_labour": 200,
				"hour_rate_rent": 1000,
				"time_in_mins": 20,
			},
		]

		test_routing_operations = [
			{"operation": "Test Operation A", "workstation": "_Test Workstation A", "time_in_mins": 30},
			{"operation": "Test Operation B", "workstation": "_Test Workstation A", "time_in_mins": 20},
		]
		setup_operations(operations)
		routing_doc = create_routing(routing_name="Routing Test", operations=test_routing_operations)
		bom_doc = setup_bom(item_code="_Testing Item", routing=routing_doc.name, currency="INR")
		self.assertEqual(routing_doc.operations[0].time_in_mins, 30)
		self.assertEqual(routing_doc.operations[1].time_in_mins, 20)
		routing_doc.operations[0].time_in_mins = 90
		routing_doc.operations[1].time_in_mins = 42.2
		routing_doc.save()
		bom_doc.update_cost()
		bom_doc.reload()
		self.assertEqual(bom_doc.operations[0].time_in_mins, 30)
		self.assertEqual(bom_doc.operations[1].time_in_mins, 20)


def setup_operations(rows):
	from erpnext.manufacturing.doctype.operation.test_operation import make_operation
	from erpnext.manufacturing.doctype.workstation.test_workstation import make_workstation

	for row in rows:
		make_workstation(row)
		make_operation(row)


def create_routing(**args):
	args = frappe._dict(args)

	doc = frappe.new_doc("Routing")
	doc.update(args)

	if not args.do_not_save:
		try:
			doc.insert()
		except frappe.DuplicateEntryError:
			doc = frappe.get_doc("Routing", args.routing_name)
			doc.delete_key("operations")
			for operation in args.operations:
				doc.append("operations", operation)

			doc.save()

	return doc


def setup_bom(**args):
	from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom

	args = frappe._dict(args)

	if not frappe.db.exists("Item", args.item_code):
		make_item(args.item_code, {"is_stock_item": 1})

	if not args.raw_materials:
		if not frappe.db.exists("Item", "Test Extra Item N-1"):
			make_item(
				"Test Extra Item N-1",
				{
					"is_stock_item": 1,
				},
			)

		args.raw_materials = ["Test Extra Item N-1"]

	name = frappe.db.get_value("BOM", {"item": args.item_code}, "name")
	if not name:
		bom_doc = make_bom(
			item=args.item_code,
			raw_materials=args.get("raw_materials"),
			routing=args.routing,
			with_operations=1,
			currency=args.currency,
			source_warehouse=args.source_warehouse,
		)
	else:
		bom_doc = frappe.get_doc("BOM", name)

	return bom_doc
