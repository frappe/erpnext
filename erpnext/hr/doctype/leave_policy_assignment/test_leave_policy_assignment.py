# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_months, get_first_day, get_last_day, getdate

from erpnext.hr.doctype.leave_application.test_leave_application import (
	get_employee,
	get_leave_period,
)
from erpnext.hr.doctype.leave_policy.test_leave_policy import create_leave_policy
from erpnext.hr.doctype.leave_policy_assignment.leave_policy_assignment import (
	create_assignment_for_multiple_employees,
)

test_dependencies = ["Employee"]


class TestLeavePolicyAssignment(FrappeTestCase):
	def setUp(self):
		for doctype in [
			"Leave Period",
			"Leave Application",
			"Leave Allocation",
			"Leave Policy Assignment",
			"Leave Ledger Entry",
		]:
			frappe.db.delete(doctype)

		employee = get_employee()
		self.original_doj = employee.date_of_joining
		self.employee = employee

	def test_grant_leaves(self):
		leave_period = get_leave_period()
		# allocation = 10
		leave_policy = create_leave_policy()
		leave_policy.submit()

		self.employee.date_of_joining = get_first_day(leave_period.from_date)
		self.employee.save()

		data = {
			"assignment_based_on": "Leave Period",
			"leave_policy": leave_policy.name,
			"leave_period": leave_period.name,
		}
		leave_policy_assignments = create_assignment_for_multiple_employees(
			[self.employee.name], frappe._dict(data)
		)
		self.assertEqual(
			frappe.db.get_value("Leave Policy Assignment", leave_policy_assignments[0], "leaves_allocated"),
			1,
		)

		leave_allocation = frappe.get_list(
			"Leave Allocation",
			filters={
				"employee": self.employee.name,
				"leave_policy": leave_policy.name,
				"leave_policy_assignment": leave_policy_assignments[0],
				"docstatus": 1,
			},
		)[0]
		leave_alloc_doc = frappe.get_doc("Leave Allocation", leave_allocation)

		self.assertEqual(leave_alloc_doc.new_leaves_allocated, 10)
		self.assertEqual(leave_alloc_doc.leave_type, "_Test Leave Type")
		self.assertEqual(getdate(leave_alloc_doc.from_date), getdate(leave_period.from_date))
		self.assertEqual(getdate(leave_alloc_doc.to_date), getdate(leave_period.to_date))
		self.assertEqual(leave_alloc_doc.leave_policy, leave_policy.name)
		self.assertEqual(leave_alloc_doc.leave_policy_assignment, leave_policy_assignments[0])

	def test_allow_to_grant_all_leave_after_cancellation_of_every_leave_allocation(self):
		leave_period = get_leave_period()
		# create the leave policy with leave type "_Test Leave Type", allocation = 10
		leave_policy = create_leave_policy()
		leave_policy.submit()

		data = {
			"assignment_based_on": "Leave Period",
			"leave_policy": leave_policy.name,
			"leave_period": leave_period.name,
		}
		leave_policy_assignments = create_assignment_for_multiple_employees(
			[self.employee.name], frappe._dict(data)
		)

		# every leave is allocated no more leave can be granted now
		self.assertEqual(
			frappe.db.get_value("Leave Policy Assignment", leave_policy_assignments[0], "leaves_allocated"),
			1,
		)
		leave_allocation = frappe.get_list(
			"Leave Allocation",
			filters={
				"employee": self.employee.name,
				"leave_policy": leave_policy.name,
				"leave_policy_assignment": leave_policy_assignments[0],
				"docstatus": 1,
			},
		)[0]

		leave_alloc_doc = frappe.get_doc("Leave Allocation", leave_allocation)
		leave_alloc_doc.cancel()
		leave_alloc_doc.delete()
		self.assertEqual(
			frappe.db.get_value("Leave Policy Assignment", leave_policy_assignments[0], "leaves_allocated"),
			0,
		)

	def test_earned_leave_allocation(self):
		leave_period = create_leave_period("Test Earned Leave Period")
		leave_type = create_earned_leave_type("Test Earned Leave")

		leave_policy = frappe.get_doc(
			{
				"doctype": "Leave Policy",
				"leave_policy_details": [{"leave_type": leave_type.name, "annual_allocation": 6}],
			}
		).submit()

		data = {
			"assignment_based_on": "Leave Period",
			"leave_policy": leave_policy.name,
			"leave_period": leave_period.name,
		}

		# second last day of the month
		# leaves allocated should be 0 since it is an earned leave and allocation happens via scheduler based on set frequency
		frappe.flags.current_date = add_days(get_last_day(getdate()), -1)
		leave_policy_assignments = create_assignment_for_multiple_employees(
			[self.employee.name], frappe._dict(data)
		)

		leaves_allocated = frappe.db.get_value(
			"Leave Allocation",
			{"leave_policy_assignment": leave_policy_assignments[0]},
			"total_leaves_allocated",
		)
		self.assertEqual(leaves_allocated, 0)

	def test_earned_leave_alloc_for_passed_months_based_on_leave_period(self):
		leave_period, leave_policy = setup_leave_period_and_policy(
			get_first_day(add_months(getdate(), -1))
		)

		# Case 1: assignment created one month after the leave period, should allocate 1 leave
		frappe.flags.current_date = get_first_day(getdate())
		data = {
			"assignment_based_on": "Leave Period",
			"leave_policy": leave_policy.name,
			"leave_period": leave_period.name,
		}
		leave_policy_assignments = create_assignment_for_multiple_employees(
			[self.employee.name], frappe._dict(data)
		)

		leaves_allocated = frappe.db.get_value(
			"Leave Allocation",
			{"leave_policy_assignment": leave_policy_assignments[0]},
			"total_leaves_allocated",
		)
		self.assertEqual(leaves_allocated, 1)

	def test_earned_leave_alloc_for_passed_months_on_month_end_based_on_leave_period(self):
		leave_period, leave_policy = setup_leave_period_and_policy(
			get_first_day(add_months(getdate(), -2))
		)
		# Case 2: assignment created on the last day of the leave period's latter month
		# should allocate 1 leave for current month even though the month has not ended
		# since the daily job might have already executed
		frappe.flags.current_date = get_last_day(getdate())

		data = {
			"assignment_based_on": "Leave Period",
			"leave_policy": leave_policy.name,
			"leave_period": leave_period.name,
		}
		leave_policy_assignments = create_assignment_for_multiple_employees(
			[self.employee.name], frappe._dict(data)
		)

		leaves_allocated = frappe.db.get_value(
			"Leave Allocation",
			{"leave_policy_assignment": leave_policy_assignments[0]},
			"total_leaves_allocated",
		)
		self.assertEqual(leaves_allocated, 3)

	def test_earned_leave_alloc_for_passed_months_with_cf_leaves_based_on_leave_period(self):
		from erpnext.hr.doctype.leave_allocation.test_leave_allocation import create_leave_allocation

		leave_period, leave_policy = setup_leave_period_and_policy(
			get_first_day(add_months(getdate(), -2))
		)
		# initial leave allocation = 5
		leave_allocation = create_leave_allocation(
			employee=self.employee.name,
			employee_name=self.employee.employee_name,
			leave_type="Test Earned Leave",
			from_date=add_months(getdate(), -12),
			to_date=add_months(getdate(), -3),
			new_leaves_allocated=5,
			carry_forward=0,
		)
		leave_allocation.submit()

		# Case 3: assignment created on the last day of the leave period's latter month with carry forwarding
		frappe.flags.current_date = get_last_day(add_months(getdate(), -1))
		data = {
			"assignment_based_on": "Leave Period",
			"leave_policy": leave_policy.name,
			"leave_period": leave_period.name,
			"carry_forward": 1,
		}
		# carry forwarded leaves = 5, 3 leaves allocated for passed months
		leave_policy_assignments = create_assignment_for_multiple_employees(
			[self.employee.name], frappe._dict(data)
		)

		details = frappe.db.get_value(
			"Leave Allocation",
			{"leave_policy_assignment": leave_policy_assignments[0]},
			["total_leaves_allocated", "new_leaves_allocated", "unused_leaves", "name"],
			as_dict=True,
		)
		self.assertEqual(details.new_leaves_allocated, 2)
		self.assertEqual(details.unused_leaves, 5)
		self.assertEqual(details.total_leaves_allocated, 7)

	def test_earned_leave_alloc_for_passed_months_based_on_joining_date(self):
		# tests leave alloc for earned leaves for assignment based on joining date in policy assignment
		leave_type = create_earned_leave_type("Test Earned Leave")
		leave_policy = frappe.get_doc(
			{
				"doctype": "Leave Policy",
				"title": "Test Leave Policy",
				"leave_policy_details": [{"leave_type": leave_type.name, "annual_allocation": 12}],
			}
		).submit()

		# joining date set to 2 months back
		self.employee.date_of_joining = get_first_day(add_months(getdate(), -2))
		self.employee.save()

		# assignment created on the last day of the current month
		frappe.flags.current_date = get_last_day(getdate())
		data = {"assignment_based_on": "Joining Date", "leave_policy": leave_policy.name}
		leave_policy_assignments = create_assignment_for_multiple_employees(
			[self.employee.name], frappe._dict(data)
		)
		leaves_allocated = frappe.db.get_value(
			"Leave Allocation",
			{"leave_policy_assignment": leave_policy_assignments[0]},
			"total_leaves_allocated",
		)
		effective_from = frappe.db.get_value(
			"Leave Policy Assignment", leave_policy_assignments[0], "effective_from"
		)
		self.assertEqual(effective_from, self.employee.date_of_joining)
		self.assertEqual(leaves_allocated, 3)

	def test_grant_leaves_on_doj_for_earned_leaves_based_on_leave_period(self):
		# tests leave alloc based on leave period for earned leaves with "based on doj" configuration in leave type
		leave_period, leave_policy = setup_leave_period_and_policy(
			get_first_day(add_months(getdate(), -2)), based_on_doj=True
		)

		# joining date set to 2 months back
		self.employee.date_of_joining = get_first_day(add_months(getdate(), -2))
		self.employee.save()

		# assignment created on the same day of the current month, should allocate leaves including the current month
		frappe.flags.current_date = get_first_day(getdate())

		data = {
			"assignment_based_on": "Leave Period",
			"leave_policy": leave_policy.name,
			"leave_period": leave_period.name,
		}
		leave_policy_assignments = create_assignment_for_multiple_employees(
			[self.employee.name], frappe._dict(data)
		)

		leaves_allocated = frappe.db.get_value(
			"Leave Allocation",
			{"leave_policy_assignment": leave_policy_assignments[0]},
			"total_leaves_allocated",
		)
		self.assertEqual(leaves_allocated, 3)

	def test_grant_leaves_on_doj_for_earned_leaves_based_on_joining_date(self):
		# tests leave alloc based on joining date for earned leaves with "based on doj" configuration in leave type
		leave_type = create_earned_leave_type("Test Earned Leave", based_on_doj=True)
		leave_policy = frappe.get_doc(
			{
				"doctype": "Leave Policy",
				"title": "Test Leave Policy",
				"leave_policy_details": [{"leave_type": leave_type.name, "annual_allocation": 12}],
			}
		).submit()

		# joining date set to 2 months back
		# leave should be allocated for current month too since this day is same as the joining day
		self.employee.date_of_joining = get_first_day(add_months(getdate(), -2))
		self.employee.save()

		# assignment created on the first day of the current month
		frappe.flags.current_date = get_first_day(getdate())
		data = {"assignment_based_on": "Joining Date", "leave_policy": leave_policy.name}
		leave_policy_assignments = create_assignment_for_multiple_employees(
			[self.employee.name], frappe._dict(data)
		)
		leaves_allocated = frappe.db.get_value(
			"Leave Allocation",
			{"leave_policy_assignment": leave_policy_assignments[0]},
			"total_leaves_allocated",
		)
		effective_from = frappe.db.get_value(
			"Leave Policy Assignment", leave_policy_assignments[0], "effective_from"
		)
		self.assertEqual(effective_from, self.employee.date_of_joining)
		self.assertEqual(leaves_allocated, 3)

	def tearDown(self):
		frappe.db.set_value("Employee", self.employee.name, "date_of_joining", self.original_doj)
		frappe.flags.current_date = None


def create_earned_leave_type(leave_type, based_on_doj=False):
	frappe.delete_doc_if_exists("Leave Type", leave_type, force=1)

	return frappe.get_doc(
		dict(
			leave_type_name=leave_type,
			doctype="Leave Type",
			is_earned_leave=1,
			earned_leave_frequency="Monthly",
			rounding=0.5,
			is_carry_forward=1,
			based_on_date_of_joining=based_on_doj,
		)
	).insert()


def create_leave_period(name, start_date=None):
	frappe.delete_doc_if_exists("Leave Period", name, force=1)
	if not start_date:
		start_date = get_first_day(getdate())

	return frappe.get_doc(
		dict(
			name=name,
			doctype="Leave Period",
			from_date=start_date,
			to_date=add_months(start_date, 12),
			company="_Test Company",
			is_active=1,
		)
	).insert()


def setup_leave_period_and_policy(start_date, based_on_doj=False):
	leave_type = create_earned_leave_type("Test Earned Leave", based_on_doj)
	leave_period = create_leave_period("Test Earned Leave Period", start_date=start_date)
	leave_policy = frappe.get_doc(
		{
			"doctype": "Leave Policy",
			"title": "Test Leave Policy",
			"leave_policy_details": [{"leave_type": leave_type.name, "annual_allocation": 12}],
		}
	).insert()

	return leave_period, leave_policy
