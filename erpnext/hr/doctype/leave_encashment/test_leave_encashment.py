# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

# class TestLeaveEncashment(unittest.TestCase):
# 	def test_leave_balance_value_and_amount(self):
# 		employee = get_employee()
# 		leave_period = get_leave_period()
# 		today = get_today()
#
# 		leave_type = frappe.get_doc(dict(
# 			leave_type_name = 'Test Leave Type',
# 			doctype = 'Leave Type',
# 			allow_encashment = 1,
# 			encashment_threshold_days = 3,
# 			earning_component = 'Leave Encashment'
# 		)).insert()
#
# 		allocate_leave(employee, leave_period, leave_type.name, 5)
#
# 		leave_encashment = frappe.get_doc(dict(
# 			doctype = 'Leave Encashment',
# 			employee = employee,
# 			leave_period = leave_period,
# 			leave_type = leave_type.name,
# 			payroll_date = today
# 		)).insert()
#
# 		self.assertEqual(leave_encashment.leave_balance, 5)
# 		self.assertEqual(leave_encashment.encashable_days, 2)
#
# 		# TODO; validate value
# 		salary_structure = get_current_structure(employee, today)
# 		self.assertEqual(leave_encashment.encashment_value,
# 			2 * frappe.db.get_value('Salary Structure', salary_structure, 'leave_encashment_amount_per_day'))


		
