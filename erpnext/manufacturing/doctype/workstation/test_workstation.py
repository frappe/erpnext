# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt
import frappe
from frappe.test_runner import make_test_records
from frappe.tests.utils import FrappeTestCase

from erpnext.manufacturing.doctype.operation.test_operation import make_operation
from erpnext.manufacturing.doctype.routing.test_routing import create_routing, setup_bom
from erpnext.manufacturing.doctype.workstation.workstation import (
	NotInWorkingHoursError,
	WorkstationHolidayError,
	check_if_within_operating_hours,
)

test_dependencies = ["Warehouse"]
test_records = frappe.get_test_records("Workstation")
make_test_records("Workstation")


class TestWorkstation(FrappeTestCase):
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
		w1.hour_rate_rent = 300
		w1.hour_rate_labour = 0
		w1.save()
		bom_doc.update_cost()
		bom_doc.reload()
		self.assertEqual(w1.hour_rate, 300)
		self.assertEqual(bom_doc.operations[0].hour_rate, 300)
		w1.hour_rate_rent = 250
		w1.save()
		# updating after setting new rates in workstations
		bom_doc.update_cost()
		bom_doc.reload()
		self.assertEqual(w1.hour_rate, 250)
		self.assertEqual(bom_doc.operations[0].hour_rate, 250)
		self.assertEqual(bom_doc.operations[1].hour_rate, 250)

		# hour_rate propagation must also refresh operating_cost (hour_rate * time_in_mins / 60)
		# on the Routing's BOM Operation rows; the 30-min op exercises the arithmetic.
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
		doc.hour_rate_rent = args.get("hour_rate_rent")
		doc.hour_rate_labour = args.get("hour_rate_labour")
		doc.workstation_type = args.get("workstation_type")
		doc.insert()

		return doc

	return frappe.get_doc("Workstation", workstation_name)
