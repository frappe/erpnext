# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.hr.doctype.leave_application.test_leave_application import get_leave_period, get_employee
from erpnext.hr.doctype.leave_policy_assignment.leave_policy_assignment import create_assignment_for_multiple_employees
from erpnext.hr.doctype.leave_policy.test_leave_policy import create_leave_policy

test_dependencies = ["Employee"]

class TestLeavePolicyAssignment(unittest.TestCase):

	def setUp(self):
		for doctype in ["Leave Application", "Leave Allocation", "Leave Policy Assignment", "Leave Ledger Entry"]:
			frappe.db.sql("delete from `tab{0}`".format(doctype)) #nosec

	def test_grant_leaves(self):
		leave_period = get_leave_period()
		employee = get_employee()

		# create the leave policy with leave type "_Test Leave Type", allocation = 10
		leave_policy = create_leave_policy()
		leave_policy.submit()


		data = {
			"assignment_based_on": "Leave Period",
			"leave_policy": leave_policy.name,
			"leave_period": leave_period.name
		}

		leave_policy_assignments = create_assignment_for_multiple_employees([employee.name], frappe._dict(data))

		leave_policy_assignment_doc = frappe.get_doc("Leave Policy Assignment", leave_policy_assignments[0])
		leave_policy_assignment_doc.reload()

		self.assertEqual(leave_policy_assignment_doc.leaves_allocated, 1)

		leave_allocation = frappe.get_list("Leave Allocation", filters={
			"employee": employee.name,
			"leave_policy":leave_policy.name,
			"leave_policy_assignment": leave_policy_assignments[0],
			"docstatus": 1})[0]

		leave_alloc_doc = frappe.get_doc("Leave Allocation", leave_allocation)

		self.assertEqual(leave_alloc_doc.new_leaves_allocated, 10)
		self.assertEqual(leave_alloc_doc.leave_type, "_Test Leave Type")
		self.assertEqual(leave_alloc_doc.from_date, leave_period.from_date)
		self.assertEqual(leave_alloc_doc.to_date, leave_period.to_date)
		self.assertEqual(leave_alloc_doc.leave_policy, leave_policy.name)
		self.assertEqual(leave_alloc_doc.leave_policy_assignment, leave_policy_assignments[0])

	def test_allow_to_grant_all_leave_after_cancellation_of_every_leave_allocation(self):
		leave_period = get_leave_period()
		employee = get_employee()

		# create the leave policy with leave type "_Test Leave Type", allocation = 10
		leave_policy = create_leave_policy()
		leave_policy.submit()


		data = {
			"assignment_based_on": "Leave Period",
			"leave_policy": leave_policy.name,
			"leave_period": leave_period.name
		}

		leave_policy_assignments = create_assignment_for_multiple_employees([employee.name], frappe._dict(data))

		leave_policy_assignment_doc = frappe.get_doc("Leave Policy Assignment", leave_policy_assignments[0])
		leave_policy_assignment_doc.reload()


		# every leave is allocated no more leave can be granted now
		self.assertEqual(leave_policy_assignment_doc.leaves_allocated, 1)

		leave_allocation = frappe.get_list("Leave Allocation", filters={
			"employee": employee.name,
			"leave_policy":leave_policy.name,
			"leave_policy_assignment": leave_policy_assignments[0],
			"docstatus": 1})[0]

		leave_alloc_doc = frappe.get_doc("Leave Allocation", leave_allocation)

		# User all allowed to grant leave when there is no allocation against assignment
		leave_alloc_doc.cancel()
		leave_alloc_doc.delete()

		leave_policy_assignment_doc.reload()


		# User are now allowed to grant leave
		self.assertEqual(leave_policy_assignment_doc.leaves_allocated, 0)

	def tearDown(self):
		for doctype in ["Leave Application", "Leave Allocation", "Leave Policy Assignment", "Leave Ledger Entry"]:
			frappe.db.sql("delete from `tab{0}`".format(doctype)) #nosec


