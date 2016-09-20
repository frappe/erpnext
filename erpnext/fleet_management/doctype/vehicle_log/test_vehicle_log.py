# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import nowdate,flt, cstr,random_string
# test_records = frappe.get_test_records('Vehicle Log')
class TestVehicleLog(unittest.TestCase):
	def test_make_vehicle_log(self):
		vehicle = frappe.get_doc({
			"doctype": "Vehicle",
			"license_plate": random_string(10).upper(),
			"make": "Maruti",
			"model": "PCM",
			"last_odometer":5000,
			"acquisition_date":frappe.utils.nowdate(),
			"location": "Mumbai",
			"chassis_no": "1234ABCD",
			"vehicle_value":frappe.utils.flt(500000)
		})
		vehicle.insert()
		license_plate = frappe.db.sql("""select license_plate from `tabVehicle` order by modified desc limit 1""")[0][0]
		vehicle_log = frappe.get_doc({
			"doctype": "Vehicle Log",
			"license_plate": cstr(license_plate).upper(),
			"employee":"EMP/0002",
			"date":frappe.utils.nowdate(),
			"odometer":5010,
			"fuel_qty":frappe.utils.flt(50),
			"price": frappe.utils.flt(500),
			"service_detail":[{
				"service_item":"Oil Change",
				"type":"Change",
				"frequency":"Monthly",
				"expense_amount":frappe.utils.flt(50)
			}
			]
		})
		vehicle_log.insert()
		vehicle_log.submit()
		return vehicle_log
