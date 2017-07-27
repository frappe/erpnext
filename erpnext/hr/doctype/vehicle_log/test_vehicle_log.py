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
		license_plate=random_string(10).upper()
		employee_id=frappe.db.sql("""select name from `tabEmployee` order by modified desc limit 1""")[0][0]
		vehicle = frappe.get_doc({
			"doctype": "Vehicle",
			"license_plate": cstr(license_plate),
			"make": "Maruti",
			"model": "PCM",
			"last_odometer":5000,
			"acquisition_date":frappe.utils.nowdate(),
			"location": "Mumbai",
			"chassis_no": "1234ABCD",
			"vehicle_value":frappe.utils.flt(500000)
		})
		try:
			vehicle.insert()
		except frappe.DuplicateEntryError:
			pass
		vehicle_log = frappe.get_doc({
			"doctype": "Vehicle Log",
			"license_plate": cstr(license_plate),
			"employee":employee_id,
			"date":frappe.utils.nowdate(),
			"odometer":5010,
			"fuel_qty":frappe.utils.flt(50),
			"price": frappe.utils.flt(500)
		})
		vehicle_log.insert()
		vehicle_log.submit()