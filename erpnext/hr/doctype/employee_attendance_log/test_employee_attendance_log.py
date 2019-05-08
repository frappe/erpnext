# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

from erpnext.hr.doctype.employee_attendance_log.employee_attendance_log import add_log_based_on_biometric_rf_id

import frappe
import unittest

class TestEmployeeAttendanceLog(unittest.TestCase):
	def test_add_log_based_on_biometric_rf_id(self):
		employee = frappe.get_doc("Employee", frappe.db.sql_list("select name from tabEmployee limit 1")[0])
		employee.biometric_rf_id = '12349'
		employee.save()

		employee_attendance_log = add_log_based_on_biometric_rf_id('12349', '2019-05-08 10:48:08.000000', 'mumbai_first_floor', 'IN')
		self.assertTrue(employee_attendance_log.employee == employee.name)
		self.assertTrue(employee_attendance_log.time == '2019-05-08 10:48:08.000000')
		self.assertTrue(employee_attendance_log.device_id == 'mumbai_first_floor')
		self.assertTrue(employee_attendance_log.log_type == 'IN')
