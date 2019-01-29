# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

# class TestCompensatoryLeaveRequest(unittest.TestCase):
# 	def get_compensatory_leave_request(self):
# 		return frappe.get_doc('Compensatory Leave Request', dict(
# 			employee = employee,
# 			work_from_date = today,
# 			work_to_date = today,
# 			reason = 'test'
# 		)).insert()
#
# 	def test_creation_of_leave_allocation(self):
# 		employee = get_employee()
# 		today = get_today()
#
# 		compensatory_leave_request = self.get_compensatory_leave_request(today)
#
# 		before = get_leave_balance(employee, compensatory_leave_request.leave_type)
#
# 		compensatory_leave_request.submit()
#
# 		self.assertEqual(get_leave_balance(employee, compensatory_leave_request.leave_type), before + 1)
#
# 	def test_max_compensatory_leave(self):
# 		employee = get_employee()
# 		today = get_today()
#
# 		compensatory_leave_request = self.get_compensatory_leave_request()
#
# 		frappe.db.set_value('Leave Type', compensatory_leave_request.leave_type, 'max_leaves_allowed', 0)
#
# 		self.assertRaises(MaxLeavesLimitCrossed, compensatory_leave_request.submit)
#
# 		frappe.db.set_value('Leave Type', compensatory_leave_request.leave_type, 'max_leaves_allowed', 10)
#
