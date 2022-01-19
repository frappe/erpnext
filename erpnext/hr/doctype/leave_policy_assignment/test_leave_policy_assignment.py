# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import add_months, get_first_day, getdate

from erpnext.hr.doctype.leave_application.test_leave_application import (
	get_employee,
	get_leave_period,
)
from erpnext.hr.doctype.leave_policy.test_leave_policy import create_leave_policy
from erpnext.hr.doctype.leave_policy_assignment.leave_policy_assignment import (
	create_assignment_for_multiple_employees,
)

test_dependencies = ["Employee"]

class TestLeavePolicyAssignment(unittest.TestCase):
	def setUp(self):
		for doctype in ["Leave Period", "Leave Application", "Leave Allocation", "Leave Policy Assignment", "Leave Ledger Entry"]:
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
		self.assertEqual(getdate(leave_alloc_doc.from_date), getdate(leave_period.from_date))
		self.assertEqual(getdate(leave_alloc_doc.to_date), getdate(leave_period.to_date))
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

	def test_earned_leave_allocation(self):
		leave_period = create_leave_period("Test Earned Leave Period")
		employee = get_employee()
		leave_type = create_earned_leave_type("Test Earned Leave")

		leave_policy = frappe.get_doc({
			"doctype": "Leave Policy",
			"title": "Test Leave Policy",
			"leave_policy_details": [{"leave_type": leave_type.name, "annual_allocation": 6}]
		}).insert()

		data = {
			"assignment_based_on": "Leave Period",
			"leave_policy": leave_policy.name,
			"leave_period": leave_period.name
		}
		leave_policy_assignments = create_assignment_for_multiple_employees([employee.name], frappe._dict(data))

		# leaves allocated should be 0 since it is an earned leave and allocation happens via scheduler based on set frequency
		leaves_allocated = frappe.db.get_value("Leave Allocation", {
			"leave_policy_assignment": leave_policy_assignments[0]
		}, "total_leaves_allocated")
		self.assertEqual(leaves_allocated, 0)

	def tearDown(self):
		frappe.db.rollback()


def create_earned_leave_type(leave_type):
	frappe.delete_doc_if_exists("Leave Type", leave_type, force=1)

	return frappe.get_doc(dict(
		leave_type_name=leave_type,
		doctype="Leave Type",
		is_earned_leave=1,
		earned_leave_frequency="Monthly",
		rounding=0.5,
		max_leaves_allowed=6
	)).insert()


def create_leave_period(name):
	frappe.delete_doc_if_exists("Leave Period", name, force=1)
	start_date = get_first_day(getdate())

	return frappe.get_doc(dict(
		name=name,
		doctype="Leave Period",
		from_date=start_date,
		to_date=add_months(start_date, 12),
		company="_Test Company",
		is_active=1
	)).insert()