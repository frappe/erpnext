# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

from erpnext.hr.doctype.employee_checkin_log.employee_checkin_log import add_employee_checkin_log_based_on_biometric_id

import frappe
import unittest

class TestEmployeeCheckinLog(unittest.TestCase):
	def test_add_employee_checkin_log_based_on_biometric_id(self):
		employee = frappe.get_doc("Employee", frappe.db.sql_list("select name from tabEmployee limit 1")[0])
		employee.biometric_id = '12349'
		employee.save()

		checkin_log = add_employee_checkin_log_based_on_biometric_id('12349', '2019-05-08 10:48:08.000000', 'mumbai_first_floor', 'IN')
		self.assertTrue(checkin_log.employee == employee.name)
		self.assertTrue(checkin_log.time == '2019-05-08 10:48:08.000000')
		self.assertTrue(checkin_log.device_id == 'mumbai_first_floor')
		self.assertTrue(checkin_log.log_type == 'IN')
