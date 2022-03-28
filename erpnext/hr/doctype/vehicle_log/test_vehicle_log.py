# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import cstr, flt, nowdate, random_string

from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.hr.doctype.vehicle_log.vehicle_log import make_expense_claim


class TestVehicleLog(unittest.TestCase):
	def setUp(self):
		employee_id = frappe.db.sql(
			"""select name from `tabEmployee` where name='testdriver@example.com'"""
		)
		self.employee_id = employee_id[0][0] if employee_id else None

		if not self.employee_id:
			self.employee_id = make_employee("testdriver@example.com", company="_Test Company")

		self.license_plate = get_vehicle(self.employee_id)

	def tearDown(self):
		frappe.delete_doc("Vehicle", self.license_plate, force=1)
		frappe.delete_doc("Employee", self.employee_id, force=1)

	def test_make_vehicle_log_and_syncing_of_odometer_value(self):
		vehicle_log = make_vehicle_log(self.license_plate, self.employee_id)

		# checking value of vehicle odometer value on submit.
		vehicle = frappe.get_doc("Vehicle", self.license_plate)
		self.assertEqual(vehicle.last_odometer, vehicle_log.odometer)

		# checking value vehicle odometer on vehicle log cancellation.
		last_odometer = vehicle_log.last_odometer
		current_odometer = vehicle_log.odometer
		distance_travelled = current_odometer - last_odometer

		vehicle_log.cancel()
		vehicle.reload()

		self.assertEqual(vehicle.last_odometer, current_odometer - distance_travelled)

		vehicle_log.delete()

	def test_vehicle_log_fuel_expense(self):
		vehicle_log = make_vehicle_log(self.license_plate, self.employee_id)

		expense_claim = make_expense_claim(vehicle_log.name)
		fuel_expense = expense_claim.expenses[0].amount
		self.assertEqual(fuel_expense, 50 * 500)

		vehicle_log.cancel()
		frappe.delete_doc("Expense Claim", expense_claim.name)
		frappe.delete_doc("Vehicle Log", vehicle_log.name)

	def test_vehicle_log_with_service_expenses(self):
		vehicle_log = make_vehicle_log(self.license_plate, self.employee_id, with_services=True)

		expense_claim = make_expense_claim(vehicle_log.name)
		expenses = expense_claim.expenses[0].amount
		self.assertEqual(expenses, 27000)

		vehicle_log.cancel()
		frappe.delete_doc("Expense Claim", expense_claim.name)
		frappe.delete_doc("Vehicle Log", vehicle_log.name)


def get_vehicle(employee_id):
	license_plate = random_string(10).upper()
	vehicle = frappe.get_doc(
		{
			"doctype": "Vehicle",
			"license_plate": cstr(license_plate),
			"make": "Maruti",
			"model": "PCM",
			"employee": employee_id,
			"last_odometer": 5000,
			"acquisition_date": nowdate(),
			"location": "Mumbai",
			"chassis_no": "1234ABCD",
			"uom": "Litre",
			"vehicle_value": flt(500000),
		}
	)
	try:
		vehicle.insert(ignore_if_duplicate=True)
	except frappe.DuplicateEntryError:
		pass
	return license_plate


def make_vehicle_log(license_plate, employee_id, with_services=False):
	vehicle_log = frappe.get_doc(
		{
			"doctype": "Vehicle Log",
			"license_plate": cstr(license_plate),
			"employee": employee_id,
			"date": nowdate(),
			"odometer": 5010,
			"fuel_qty": flt(50),
			"price": flt(500),
		}
	)

	if with_services:
		vehicle_log.append(
			"service_detail",
			{
				"service_item": "Oil Change",
				"type": "Inspection",
				"frequency": "Mileage",
				"expense_amount": flt(500),
			},
		)
		vehicle_log.append(
			"service_detail",
			{
				"service_item": "Wheels",
				"type": "Change",
				"frequency": "Half Yearly",
				"expense_amount": flt(1500),
			},
		)

	vehicle_log.save()
	vehicle_log.submit()

	return vehicle_log
