# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import today, add_months
from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.hr.doctype.salary_structure.test_salary_structure import make_salary_structure
from erpnext.hr.doctype.leave_period.test_leave_period import create_leave_period

test_dependencies = ["Leave Type"]

class TestLeaveEncashment(unittest.TestCase):
	def setUp(self):
		frappe.db.sql('''delete from `tabLeave Period`''')
	def test_leave_balance_value_and_amount(self):
		employee = "test_employee_encashment@salary.com"
		leave_type = "_Test Leave Type Encashment"

		# create the leave policy
		leave_policy = frappe.get_doc({
			"doctype": "Leave Policy",
			"leave_policy_details": [{
				"leave_type": leave_type,
				"annual_allocation": 10
			}]
		}).insert()
		leave_policy.submit()

		# create employee, salary structure and assignment
		employee = make_employee(employee)
		frappe.db.set_value("Employee", employee, "leave_policy", leave_policy.name) 
		salary_structure = make_salary_structure("Salary Structure for Encashment", "Monthly", employee,
			other_details={"leave_encashment_amount_per_day": 50})

		# create the leave period and assign the leaves
		leave_period = create_leave_period(add_months(today(), -3), add_months(today(), 3))
		leave_period.grant_leave_allocation(employee=employee)

		leave_encashment = frappe.get_doc(dict(
			doctype = 'Leave Encashment',
			employee = employee,
			leave_type = leave_type,
			leave_period = leave_period.name,
			payroll_date = today()
		)).insert()

		self.assertEqual(leave_encashment.leave_balance, 10)
		self.assertEqual(leave_encashment.encashable_days, 5)
		self.assertEqual(leave_encashment.encashment_amount, 250)

		leave_encashment.submit()
		self.assertTrue(frappe.db.get_value("Leave Encashment", leave_encashment.name, "additional_salary"))
