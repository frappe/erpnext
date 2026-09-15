# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt
import frappe
from frappe import _

from erpnext.manufacturing.doctype.job_card.mapper import make_stock_entry
from erpnext.manufacturing.doctype.operation.test_operation import make_operation
from erpnext.manufacturing.doctype.routing.test_routing import create_routing, setup_bom
from erpnext.manufacturing.doctype.workstation.workstation import (
	NotInWorkingHoursError,
	WorkstationHolidayError,
	check_if_within_operating_hours,
	get_raw_materials,
	update_job_card,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestWorkstation(ERPNextTestSuite):
	def test_get_raw_materials_without_items(self):
		for skip_transfer, backflush_from_wip in ((0, 0), (1, 0), (1, 1)):
			with self.subTest(skip_transfer=skip_transfer, backflush_from_wip=backflush_from_wip):
				job_card = frappe.get_doc(
					{
						"doctype": "Job Card",
						"company": "_Test Company",
						"skip_material_transfer": skip_transfer,
						"backflush_from_wip_warehouse": backflush_from_wip,
						"wip_warehouse": "_Test Warehouse 1 - _TC",
					}
				).insert(ignore_mandatory=True)

				for method in (get_raw_materials, make_stock_entry):
					with self.subTest(method=method.__name__):
						with self.assertRaisesRegex(
							frappe.ValidationError, "This Job Card has no raw materials to transfer"
						):
							method(job_card.name)

				job_card.reload()
				self.assertFalse(job_card.items)
				self.assertFalse(frappe.db.exists("Stock Entry", {"job_card": job_card.name}))

	def test_get_raw_materials_availability(self):
		for skip_transfer, backflush_from_wip, transferred_qty in (
			(0, 0, 2),
			(0, 0, 5),
			(1, 0, 0),
			(1, 1, 0),
		):
			with self.subTest(
				skip_transfer=skip_transfer,
				backflush_from_wip=backflush_from_wip,
				transferred_qty=transferred_qty,
			):
				job_card = frappe.get_doc(
					{
						"doctype": "Job Card",
						"company": "_Test Company",
						"skip_material_transfer": skip_transfer,
						"backflush_from_wip_warehouse": backflush_from_wip,
						"wip_warehouse": "_Test Warehouse 1 - _TC",
						"items": [
							{
								"item_code": "_Test Item",
								"source_warehouse": "_Test Warehouse - _TC",
								"required_qty": 5,
								"transferred_qty": transferred_qty,
							},
						],
					}
				).insert(ignore_mandatory=True)

				materials = get_raw_materials(job_card.name)

				self.assertEqual(len(materials), 1)
				material = materials[0]
				warehouse = "_Test Warehouse 1 - _TC" if backflush_from_wip else "_Test Warehouse - _TC"
				stock_qty = (
					frappe.db.get_value(
						"Bin", {"item_code": "_Test Item", "warehouse": warehouse}, "actual_qty"
					)
					or 0
				)
				self.assertEqual(material.item_code, "_Test Item")
				self.assertEqual(material.required_qty, 5)
				self.assertEqual(material.transferred_qty, transferred_qty)
				self.assertEqual(material.warehouse, warehouse)
				self.assertEqual(material.stock_qty, stock_qty)
				self.assertEqual(
					material.material_availability_status,
					int(stock_qty >= 5) if skip_transfer else int(transferred_qty >= 5),
				)

	def test_update_job_card_rejects_disallowed_method(self):
		# The whitelisted update_job_card endpoint must only run an allowlisted set of Job Card
		# methods. An arbitrary method name must be rejected (PermissionError) before the document
		# is even loaded, so this needs no Job Card to exist.
		self.assertRaises(
			frappe.PermissionError,
			update_job_card,
			"NON-EXISTENT-JOB-CARD",
			"delete",
		)

	def test_validate_timings(self):
		check_if_within_operating_hours(
			"_Test Workstation 1", "Operation 1", "2013-02-02 11:00:00", "2013-02-02 19:00:00"
		)
		check_if_within_operating_hours(
			"_Test Workstation 1", "Operation 1", "2013-02-02 10:00:00", "2013-02-02 20:00:00"
		)
		self.assertRaises(
			NotInWorkingHoursError,
			check_if_within_operating_hours,
			"_Test Workstation 1",
			"Operation 1",
			"2013-02-02 05:00:00",
			"2013-02-02 20:00:00",
		)
		self.assertRaises(
			NotInWorkingHoursError,
			check_if_within_operating_hours,
			"_Test Workstation 1",
			"Operation 1",
			"2013-02-02 05:00:00",
			"2013-02-02 20:00:00",
		)
		self.assertRaises(
			WorkstationHolidayError,
			check_if_within_operating_hours,
			"_Test Workstation 1",
			"Operation 1",
			"2013-02-01 10:00:00",
			"2013-02-02 20:00:00",
		)

	def test_update_bom_operation_rate(self):
		operations = [
			{
				"operation": "Test Operation A",
				"workstation": "_Test Workstation A",
				"hour_rate_rent": 300,
				"time_in_mins": 60,
			},
			{
				"operation": "Test Operation B",
				"workstation": "_Test Workstation B",
				"hour_rate_rent": 1000,
				"time_in_mins": 60,
			},
		]

		for row in operations:
			make_workstation(row)
			make_operation(row)

		test_routing_operations = [
			{"operation": "Test Operation A", "workstation": "_Test Workstation A", "time_in_mins": 60},
			{"operation": "Test Operation B", "workstation": "_Test Workstation A", "time_in_mins": 30},
		]
		routing_doc = create_routing(routing_name="Routing Test", operations=test_routing_operations)
		bom_doc = setup_bom(item_code="_Testing Item", routing=routing_doc.name, currency="INR")
		w1 = frappe.get_doc("Workstation", "_Test Workstation A")
		# resets values
		for row in w1.workstation_costs:
			if row.operating_component == _("Rent"):
				row.operating_cost = 300
				break

		w1.save()
		bom_doc.update_cost()
		bom_doc.reload()
		self.assertEqual(w1.hour_rate, 300)
		self.assertEqual(bom_doc.operations[0].hour_rate, 300)

		for row in w1.workstation_costs:
			if row.operating_component == _("Rent"):
				row.operating_cost = 250
				break

		w1.save()
		# updating after setting new rates in workstations
		bom_doc.update_cost()
		bom_doc.reload()
		self.assertEqual(w1.hour_rate, 250)
		self.assertEqual(bom_doc.operations[0].hour_rate, 250)
		self.assertEqual(bom_doc.operations[1].hour_rate, 250)

		# update_bom_operation() (run on w1.save()) must write the new rate directly onto the
		# Routing's BOM Operation rows. This is the converted query's own effect (not the BOM
		# update_cost above) and is what silently skipped on Postgres when parenttype was 'routing'.
		# It must also refresh operating_cost (hour_rate * time_in_mins / 60); the 30-min op
		# exercises the arithmetic rather than a plain rate copy.
		for operation, expected_operating_cost in (("Test Operation A", 250), ("Test Operation B", 125)):
			hour_rate, operating_cost = frappe.db.get_value(
				"BOM Operation",
				{"parent": routing_doc.name, "parenttype": "Routing", "operation": operation},
				["hour_rate", "operating_cost"],
			)
			self.assertEqual(hour_rate, 250)
			self.assertEqual(operating_cost, expected_operating_cost)


def make_workstation(*args, **kwargs):
	args = args if args else kwargs
	if isinstance(args, tuple):
		args = args[0]

	args = frappe._dict(args)

	workstation_name = args.workstation_name or args.workstation
	if not frappe.db.exists("Workstation", workstation_name):
		doc = frappe.get_doc({"doctype": "Workstation", "workstation_name": workstation_name})
		if args.get("hour_rate_rent"):
			doc.append(
				"workstation_costs",
				{
					"operating_component": _("Rent"),
					"operating_cost": args.get("hour_rate_rent"),
				},
			)

		if args.get("hour_rate_labour"):
			doc.append(
				"workstation_costs",
				{
					"operating_component": _("Wages"),
					"operating_cost": args.get("hour_rate_labour"),
				},
			)

		doc.workstation_type = args.get("workstation_type")
		doc.insert()

		return doc

	return frappe.get_doc("Workstation", workstation_name)
