# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_months, nowdate

import erpnext
from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.payroll.doctype.salary_component.test_salary_component import create_salary_component
from erpnext.payroll.doctype.salary_slip.test_salary_slip import (
	make_employee_salary_slip,
	setup_test,
)
from erpnext.payroll.doctype.salary_structure.test_salary_structure import make_salary_structure


class TestAdditionalSalary(FrappeTestCase):
	def setUp(self):
		setup_test()

	def test_recurring_additional_salary(self):
		amount = 0
		salary_component = None
		emp_id = make_employee("test_additional@salary.com")
		frappe.db.set_value("Employee", emp_id, "relieving_date", add_days(nowdate(), 1800))
		salary_structure = make_salary_structure(
			"Test Salary Structure Additional Salary", "Monthly", employee=emp_id
		)
		add_sal = get_additional_salary(emp_id)

		ss = make_employee_salary_slip(
			"test_additional@salary.com", "Monthly", salary_structure=salary_structure.name
		)
		for earning in ss.earnings:
			if earning.salary_component == "Recurring Salary Component":
				amount = earning.amount
				salary_component = earning.salary_component
				break

		self.assertEqual(amount, add_sal.amount)
		self.assertEqual(salary_component, add_sal.salary_component)

	def test_non_recurring_additional_salary(self):
		amount = 0
		salary_component = None
		date = nowdate()

		emp_id = make_employee("test_additional@salary.com")
		frappe.db.set_value("Employee", emp_id, "relieving_date", add_days(date, 1800))
		salary_structure = make_salary_structure(
			"Test Salary Structure Additional Salary", "Monthly", employee=emp_id
		)
		add_sal = get_additional_salary(emp_id, recurring=False, payroll_date=date)

		ss = make_employee_salary_slip(
			"test_additional@salary.com", "Monthly", salary_structure=salary_structure.name
		)

		amount, salary_component = None, None
		for earning in ss.earnings:
			if earning.salary_component == "Recurring Salary Component":
				amount = earning.amount
				salary_component = earning.salary_component
				break

		self.assertEqual(amount, add_sal.amount)
		self.assertEqual(salary_component, add_sal.salary_component)

		# should not show up in next months
		ss.posting_date = add_months(date, 1)
		ss.start_date = ss.end_date = None
		ss.earnings = []
		ss.deductions = []
		ss.save()

		amount, salary_component = None, None
		for earning in ss.earnings:
			if earning.salary_component == "Recurring Salary Component":
				amount = earning.amount
				salary_component = earning.salary_component
				break

		self.assertIsNone(amount)
		self.assertIsNone(salary_component)


def get_additional_salary(emp_id, recurring=True, payroll_date=None):
	create_salary_component("Recurring Salary Component")
	add_sal = frappe.new_doc("Additional Salary")
	add_sal.employee = emp_id
	add_sal.salary_component = "Recurring Salary Component"

	add_sal.is_recurring = 1 if recurring else 0
	add_sal.from_date = add_days(nowdate(), -50)
	add_sal.to_date = add_days(nowdate(), 180)
	add_sal.payroll_date = payroll_date

	add_sal.amount = 5000
	add_sal.currency = erpnext.get_default_currency()
	add_sal.save()
	add_sal.submit()

	return add_sal
