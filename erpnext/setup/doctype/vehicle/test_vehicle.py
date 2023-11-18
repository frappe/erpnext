# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import random_string

# test_records = frappe.get_test_records('Vehicle')


class TestVehicle(unittest.TestCase):
	def test_make_vehicle(self):
		vehicle = frappe.get_doc(
			{
				"doctype": "Vehicle",
				"idenifier": random_string(10).upper(),
				"manufacturer": "Maruti",
				"model": "PCM",
				"last_odometer": 5000,
				"acquisition_date": frappe.utils.nowdate(),
				"location": "Mumbai",
				"serial_no": "1234ABCD",
				"vehicle_value": frappe.utils.flt(500000),
			}
		)
		vehicle.insert()
