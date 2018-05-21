# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

# class TestLeavePeriod(unittest.TestCase):
# 	def test_leave_grant(self):
# 		employee = get_employee()
# 		leave_policy = get_leave_policy()
# 		leave_period = get_leave_period()
#
# 		frappe.db.set_value('Employee', employee, 'leave_policy', leave_policy)
#
# 		leave_period.employee = employee
#
# 		clear_leave_allocation(employee)
#
# 		leave_period.grant_leaves()
#
# 		for d in leave_policy:
# 			self.assertEqual(get_leave_balance(employee, d.leave_type), d.annual_allocation)
#
# 		return leave_period
#
# 	def test_duplicate_grant(self):
# 		leave_period = self.test_leave_grant()
# 		self.assertRaises(DuplicateLeaveGrant, leave_period.grant_leaves)
#
