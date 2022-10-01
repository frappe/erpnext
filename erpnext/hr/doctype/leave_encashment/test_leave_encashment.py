# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, get_year_ending, get_year_start, getdate

from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.hr.doctype.holiday_list.test_holiday_list import set_holiday_list
from erpnext.hr.doctype.leave_period.test_leave_period import create_leave_period
from erpnext.hr.doctype.leave_policy.test_leave_policy import create_leave_policy
from erpnext.hr.doctype.leave_policy_assignment.leave_policy_assignment import (
	create_assignment_for_multiple_employees,
)
from erpnext.payroll.doctype.salary_slip.test_salary_slip import (
	make_holiday_list,
	make_leave_application,
)
from erpnext.payroll.doctype.salary_structure.test_salary_structure import make_salary_structure

test_records = frappe.get_test_records("Leave Type")


class TestLeaveEncashment(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Leave Period")
		frappe.db.delete("Leave Policy Assignment")
		frappe.db.delete("Leave Allocation")
		frappe.db.delete("Leave Ledger Entry")
		frappe.db.delete("Additional Salary")
		frappe.db.delete("Leave Encashment")

		if not frappe.db.exists("Leave Type", "_Test Leave Type Encashment"):
			frappe.get_doc(test_records[2]).insert()

		date = getdate()
		year_start = getdate(get_year_start(date))
		year_end = getdate(get_year_ending(date))

		make_holiday_list("_Test Leave Encashment", year_start, year_end)

		# create the leave policy
		leave_policy = create_leave_policy(
			leave_type="_Test Leave Type Encashment", annual_allocation=10
		)
		leave_policy.submit()

		# create employee, salary structure and assignment
		self.employee = make_employee("test_employee_encashment@example.com", company="_Test Company")

		self.leave_period = create_leave_period(year_start, year_end, "_Test Company")

		data = {
			"assignment_based_on": "Leave Period",
			"leave_policy": leave_policy.name,
			"leave_period": self.leave_period.name,
		}

		leave_policy_assignments = create_assignment_for_multiple_employees(
			[self.employee], frappe._dict(data)
		)

		salary_structure = make_salary_structure(
			"Salary Structure for Encashment",
			"Monthly",
			self.employee,
			other_details={"leave_encashment_amount_per_day": 50},
		)

	@set_holiday_list("_Test Leave Encashment", "_Test Company")
	def test_leave_balance_value_and_amount(self):
		leave_encashment = frappe.get_doc(
			dict(
				doctype="Leave Encashment",
				employee=self.employee,
				leave_type="_Test Leave Type Encashment",
				leave_period=self.leave_period.name,
				encashment_date=self.leave_period.to_date,
				currency="INR",
			)
		).insert()

		self.assertEqual(leave_encashment.leave_balance, 10)
		self.assertEqual(leave_encashment.encashable_days, 5)
		self.assertEqual(leave_encashment.encashment_amount, 250)

		leave_encashment.submit()

		# assert links
		add_sal = frappe.get_all("Additional Salary", filters={"ref_docname": leave_encashment.name})[0]
		self.assertTrue(add_sal)

	@set_holiday_list("_Test Leave Encashment", "_Test Company")
	def test_leave_balance_value_with_leaves_and_amount(self):
		date = self.leave_period.from_date
		leave_application = make_leave_application(
			self.employee, date, add_days(date, 3), "_Test Leave Type Encashment"
		)
		leave_application.reload()

		leave_encashment = frappe.get_doc(
			dict(
				doctype="Leave Encashment",
				employee=self.employee,
				leave_type="_Test Leave Type Encashment",
				leave_period=self.leave_period.name,
				encashment_date=self.leave_period.to_date,
				currency="INR",
			)
		).insert()

		self.assertEqual(leave_encashment.leave_balance, 10 - leave_application.total_leave_days)
		# encashable days threshold is 5, total leaves are 6, so encashable days = 6-5 = 1
		# with charge of 50 per day
		self.assertEqual(leave_encashment.encashable_days, leave_encashment.leave_balance - 5)
		self.assertEqual(leave_encashment.encashment_amount, 50)

		leave_encashment.submit()

		# assert links
		add_sal = frappe.get_all("Additional Salary", filters={"ref_docname": leave_encashment.name})[0]
		self.assertTrue(add_sal)

	@set_holiday_list("_Test Leave Encashment", "_Test Company")
	def test_creation_of_leave_ledger_entry_on_submit(self):
		leave_encashment = frappe.get_doc(
			dict(
				doctype="Leave Encashment",
				employee=self.employee,
				leave_type="_Test Leave Type Encashment",
				leave_period=self.leave_period.name,
				encashment_date=self.leave_period.to_date,
				currency="INR",
			)
		).insert()

		leave_encashment.submit()

		leave_ledger_entry = frappe.get_all(
			"Leave Ledger Entry", fields="*", filters=dict(transaction_name=leave_encashment.name)
		)

		self.assertEqual(len(leave_ledger_entry), 1)
		self.assertEqual(leave_ledger_entry[0].employee, leave_encashment.employee)
		self.assertEqual(leave_ledger_entry[0].leave_type, leave_encashment.leave_type)
		self.assertEqual(leave_ledger_entry[0].leaves, leave_encashment.encashable_days * -1)

		# check if leave ledger entry is deleted on cancellation

		frappe.db.sql(
			"Delete from `tabAdditional Salary` WHERE ref_docname = %s", (leave_encashment.name)
		)

		leave_encashment.cancel()
		self.assertFalse(
			frappe.db.exists("Leave Ledger Entry", {"transaction_name": leave_encashment.name})
		)
