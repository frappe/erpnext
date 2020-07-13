# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import nowdate,flt,cstr,random_string

class TestVehicleLog(unittest.TestCase):
	def test_make_vehicle_log_and_syncing_of_odometer_value(self):
		employee_id = frappe.db.sql("""select name from `tabEmployee` where status='Active' order by modified desc limit 1""")
		employee_id = employee_id[0][0] if employee_id else None

		vehicle = get_vehicle()
		vehicle.submit()

		#checking opening log for vehicle
		check_opening_log = frappe.db.exists("Vehicle Log",{"is_opening": 1, "license_plate": vehicle.name})

		self.assertIsNotNone(check_opening_log)

		vehicle_log = frappe.get_doc({
			"doctype": "Vehicle Log",
			"license_plate": vehicle.name,
			"employee":employee_id,
			"date":frappe.utils.nowdate(),
			"odometer":5010,
			"fuel_qty":frappe.utils.flt(50),
			"price": frappe.utils.flt(500)
		})
		vehicle_log.save()
		vehicle_log.submit()

		#checking value of vehicle odometer value on submit.
		vehicle.reload()
		self.assertEqual(vehicle.last_odometer_value, vehicle_log.odometer)

def get_vehicle():
	license_plate=random_string(10).upper()
	vehicle = frappe.get_doc({
			"doctype": "Vehicle",
			"license_plate": cstr(license_plate),
			"make": "Maruti",
			"model": "PCM",
			"initial_odometer_value":5000,
			"acquisition_date":frappe.utils.nowdate(),
			"location": "Mumbai",
			"chassis_no": "1234ABCD",
			"uom": "Litre",
			"vehicle_value":frappe.utils.flt(500000)
		})
	try:
		vehicle.save()
	except frappe.DuplicateEntryError:
		pass
	return vehicle