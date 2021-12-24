# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe
from frappe.utils import add_days, nowdate

import erpnext
from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.payroll.doctype.salary_component.test_salary_component import create_salary_component
from erpnext.payroll.doctype.salary_slip.test_salary_slip import (
	make_employee_salary_slip,
	setup_test,
)
from erpnext.payroll.doctype.salary_structure.test_salary_structure import make_salary_structure


class TestAdditionalSalary(unittest.TestCase):

	def setUp(self):
		setup_test()

	def tearDown(self):
		for dt in ["Salary Slip", "Additional Salary", "Salary Structure Assignment", "Salary Structure"]:
			frappe.db.sql("delete from `tab%s`" % dt)

	def test_recurring_additional_salary(self):
		amount = 0
		salary_component = None
		emp_id = make_employee("test_additional@salary.com")
		frappe.db.set_value("Employee", emp_id, "relieving_date", add_days(nowdate(), 1800))
		salary_structure = make_salary_structure("Test Salary Structure Additional Salary", "Monthly", employee=emp_id)
		add_sal = get_additional_salary(emp_id)

		ss = make_employee_salary_slip("test_additional@salary.com", "Monthly", salary_structure=salary_structure.name)
		for earning in ss.earnings:
			if earning.salary_component == "Recurring Salary Component":
				amount = earning.amount
				salary_component = earning.salary_component

		self.assertEqual(amount, add_sal.amount)
		self.assertEqual(salary_component, add_sal.salary_component)

def get_additional_salary(emp_id):
	create_salary_component("Recurring Salary Component")
	add_sal = frappe.new_doc("Additional Salary")
	add_sal.employee = emp_id
	add_sal.salary_component = "Recurring Salary Component"
	add_sal.is_recurring = 1
	add_sal.from_date = add_days(nowdate(), -50)
	add_sal.to_date = add_days(nowdate(), 180)
	add_sal.amount = 5000
	add_sal.currency = erpnext.get_default_currency()
	add_sal.save()
	add_sal.submit()

	return add_sal
