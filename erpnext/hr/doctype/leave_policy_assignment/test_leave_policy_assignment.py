# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import add_months, get_first_day, get_last_day, getdate

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

	def test_earned_leave_allocation_for_passed_months(self):
		employee = get_employee()
		leave_type = create_earned_leave_type("Test Earned Leave")
		leave_period = create_leave_period("Test Earned Leave Period",
			start_date=get_first_day(add_months(getdate(), -1)))
		leave_policy = frappe.get_doc({
			"doctype": "Leave Policy",
			"title": "Test Leave Policy",
			"leave_policy_details": [{"leave_type": leave_type.name, "annual_allocation": 12}]
		}).insert()

		# Case 1: assignment created one month after the leave period, should allocate 1 leave
		frappe.flags.current_date = get_first_day(getdate())
		data = {
			"assignment_based_on": "Leave Period",
			"leave_policy": leave_policy.name,
			"leave_period": leave_period.name
		}
		leave_policy_assignments = create_assignment_for_multiple_employees([employee.name], frappe._dict(data))

		leaves_allocated = frappe.db.get_value("Leave Allocation", {
			"leave_policy_assignment": leave_policy_assignments[0]
		}, "total_leaves_allocated")
		self.assertEqual(leaves_allocated, 1)

	def test_earned_leave_allocation_for_passed_months_on_month_end(self):
		employee = get_employee()
		leave_type = create_earned_leave_type("Test Earned Leave")
		leave_period = create_leave_period("Test Earned Leave Period",
			start_date=get_first_day(add_months(getdate(), -2)))
		leave_policy = frappe.get_doc({
			"doctype": "Leave Policy",
			"title": "Test Leave Policy",
			"leave_policy_details": [{"leave_type": leave_type.name, "annual_allocation": 12}]
		}).insert()

		# Case 2: assignment created on the last day of the leave period's latter month
		# should allocate 1 leave for current month even though the month has not ended
		# since the daily job might have already executed
		frappe.flags.current_date = get_last_day(getdate())

		data = {
			"assignment_based_on": "Leave Period",
			"leave_policy": leave_policy.name,
			"leave_period": leave_period.name
		}
		leave_policy_assignments = create_assignment_for_multiple_employees([employee.name], frappe._dict(data))

		leaves_allocated = frappe.db.get_value("Leave Allocation", {
			"leave_policy_assignment": leave_policy_assignments[0]
		}, "total_leaves_allocated")
		self.assertEqual(leaves_allocated, 3)

		# if the daily job is not completed yet, there is another check present
		# to ensure leave is not already allocated to avoid duplication
		from erpnext.hr.utils import allocate_earned_leaves
		allocate_earned_leaves()

		leaves_allocated = frappe.db.get_value("Leave Allocation", {
			"leave_policy_assignment": leave_policy_assignments[0]
		}, "total_leaves_allocated")
		self.assertEqual(leaves_allocated, 3)

	def test_earned_leave_allocation_for_passed_months_with_carry_forwarded_leaves(self):
		from erpnext.hr.doctype.leave_allocation.test_leave_allocation import create_leave_allocation

		employee = get_employee()
		leave_type = create_earned_leave_type("Test Earned Leave")
		leave_period = create_leave_period("Test Earned Leave Period",
			start_date=get_first_day(add_months(getdate(), -2)))
		leave_policy = frappe.get_doc({
			"doctype": "Leave Policy",
			"title": "Test Leave Policy",
			"leave_policy_details": [{"leave_type": leave_type.name, "annual_allocation": 12}]
		}).insert()

		# initial leave allocation = 5
		leave_allocation = create_leave_allocation(
			employee=employee.name,
			employee_name=employee.employee_name,
			leave_type=leave_type.name,
			from_date=add_months(getdate(), -12),
			to_date=add_months(getdate(), -3),
			new_leaves_allocated=5,
			carry_forward=0)
		leave_allocation.submit()

		# Case 3: assignment created on the last day of the leave period's latter month with carry forwarding
		frappe.flags.current_date = get_last_day(add_months(getdate(), -1))

		data = {
			"assignment_based_on": "Leave Period",
			"leave_policy": leave_policy.name,
			"leave_period": leave_period.name,
			"carry_forward": 1
		}
		# carry forwarded leaves = 5, 3 leaves allocated for passed months
		leave_policy_assignments = create_assignment_for_multiple_employees([employee.name], frappe._dict(data))

		details = frappe.db.get_value("Leave Allocation", {
			"leave_policy_assignment": leave_policy_assignments[0]
		}, ["total_leaves_allocated", "new_leaves_allocated", "unused_leaves", "name"], as_dict=True)
		self.assertEqual(details.new_leaves_allocated, 2)
		self.assertEqual(details.unused_leaves, 5)
		self.assertEqual(details.total_leaves_allocated, 7)

		# if the daily job is not completed yet, there is another check present
		# to ensure leave is not already allocated to avoid duplication
		from erpnext.hr.utils import is_earned_leave_already_allocated
		frappe.flags.current_date = get_last_day(getdate())

		allocation = frappe.get_doc('Leave Allocation', details.name)
		# 1 leave is still pending to be allocated, irrespective of carry forwarded leaves
		self.assertFalse(is_earned_leave_already_allocated(allocation, leave_policy.leave_policy_details[0].annual_allocation))

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
		is_carry_forward=1
	)).insert()


def create_leave_period(name, start_date=None):
	frappe.delete_doc_if_exists("Leave Period", name, force=1)
	if not start_date:
		start_date = get_first_day(getdate())

	return frappe.get_doc(dict(
		name=name,
		doctype="Leave Period",
		from_date=start_date,
		to_date=add_months(start_date, 12),
		company="_Test Company",
		is_active=1
	)).insert()