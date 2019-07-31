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
from erpnext.hr.doctype.leave_policy.test_leave_policy import create_leave_policy\

test_dependencies = ["Leave Type"]

class TestLeaveEncashment(unittest.TestCase):
	def setUp(self):
		frappe.db.sql('''delete from `tabLeave Period`''')
		frappe.db.sql('''delete from `tabLeave Allocation`''')
		frappe.db.sql('''delete from `tabLeave Ledger Entry`''')
		frappe.db.sql('''delete from `tabAdditional Salary`''')

		# create the leave policy
		leave_policy = create_leave_policy(
			leave_type="_Test Leave Type Encashment",
			annual_allocation=10)
		leave_policy.submit()

		# create employee, salary structure and assignment
		self.employee = make_employee("test_employee_encashment@example.com")

		frappe.db.set_value("Employee", self.employee, "leave_policy", leave_policy.name)

		salary_structure = make_salary_structure("Salary Structure for Encashment", "Monthly", self.employee,
			other_details={"leave_encashment_amount_per_day": 50})

		# create the leave period and assign the leaves
		self.leave_period = create_leave_period(add_months(today(), -3), add_months(today(), 3))
		self.leave_period.grant_leave_allocation(employee=self.employee)

	def test_leave_balance_value_and_amount(self):
		frappe.db.sql('''delete from `tabLeave Encashment`''')
		leave_encashment = frappe.get_doc(dict(
			doctype='Leave Encashment',
			employee=self.employee,
			leave_type="_Test Leave Type Encashment",
			leave_period=self.leave_period.name,
			payroll_date=today()
		)).insert()

		self.assertEqual(leave_encashment.leave_balance, 10)
		self.assertEqual(leave_encashment.encashable_days, 5)
		self.assertEqual(leave_encashment.encashment_amount, 250)

		leave_encashment.submit()
		self.assertTrue(frappe.db.get_value("Leave Encashment", leave_encashment.name, "additional_salary"))

	def test_creation_of_leave_ledger_entry_on_submit(self):
		frappe.db.sql('''delete from `tabLeave Encashment`''')
		leave_encashment = frappe.get_doc(dict(
			doctype='Leave Encashment',
			employee=self.employee,
			leave_type="_Test Leave Type Encashment",
			leave_period=self.leave_period.name,
			payroll_date=today()
		)).insert()

		leave_encashment.submit()

		leave_ledger_entry = frappe.get_all('Leave Ledger Entry', fields='*', filters=dict(transaction_name=leave_encashment.name))

		self.assertEquals(len(leave_ledger_entry), 1)
		self.assertEquals(leave_ledger_entry[0].employee, leave_encashment.employee)
		self.assertEquals(leave_ledger_entry[0].leave_type, leave_encashment.leave_type)
		self.assertEquals(leave_ledger_entry[0].leaves, leave_encashment.encashable_days *  -1)

		# check if leave ledger entry is deleted on cancellation
		leave_encashment.cancel()
		self.assertFalse(frappe.db.exists("Leave Ledger Entry", {'transaction_name':leave_encashment.name}))
