# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
import calendar
from frappe.utils import nowdate, add_days, add_months, cint, getdate
from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.hr.doctype.additional_salary.test_additional_salary import create_salary_component_if_missing


class TestDeductSalaryforPreviousLeaves(unittest.TestCase):
	def setUp(self):
		frappe.db.sql("delete from `tabLeave Application`")
		frappe.db.sql("delete from `tabAdditional Salary`")

		if not frappe.db.exists("Leave Type", "_Test Leave Type Negative"):
			frappe.get_doc({
				"doctype": "Leave Type",
				"leave_type_name": "_Test Leave Type Negative",
				"allow_negative": 1,
				"include_holiday": 1
			}).insert()

	def test_salary_deduction_for_previous_leaves(self):
		leave_type = "_Test Leave Type Negative"
		employee = make_employee("test_email@erpnext.org")
		salary_component = "Salary Deduction for Previous Leaves"

		create_salary_structure(employee)
		create_salary_component_if_missing(salary_component=salary_component, type="Deduction")

		dt = getdate(nowdate())
		days_in_month = cint(calendar.monthrange(cint(dt.year) ,cint(dt.month))[1])

		ds = frappe.new_doc("Deduct Salary for Previous Leaves")
		ds.employee = employee
		ds.payroll_date = dt
		ds.salary_component = salary_component
		ds.append("leave_periods", {
			"leave_type": leave_type,
			"from_date": add_months(dt, -2),
			"to_date": add_days(add_months(dt, -2), 2),
			"total_days": 2
		})
		ds.submit()

		leaves = frappe.db.sql("""select total_leave_days from `tabLeave Application`
			where employee=%s and leave_type=%s and docstatus=1""", (employee, leave_type))[0][0]
		self.assertEqual(leaves, 2)

		additional_salary = frappe.db.sql("select amount from `tabAdditional Salary` where salary_component=%s", salary_component)[0][0]
		self.assertEqual(additional_salary, 100*2/days_in_month)

def create_salary_structure(employee):
	create_salary_component_if_missing(salary_component="Basic prorated based on attendance", prorated_based_on_attendance=1)

	if not frappe.db.exists("Salary Structure", "SS-0001"):
		ss = frappe.new_doc("Salary Structure")
		ss.name = "SS-0001"
		ss.company = "_Test Company"
		ss.append("earnings", {
			"salary_component": "Basic prorated based on attendance",
			"prorated_based_on_attendance": 1,
			"amount": 100
		})
		ss.save()
		ss.submit()

	if not frappe.db.get_value("Salary Structure Assignment", {"salary_structure": "SS-0001", "employee": employee}):
		ssa = frappe.new_doc("Salary Structure Assignment")
		ssa.employee = employee
		ssa.salary_structure = "SS-0001"
		ssa.from_date = add_months(nowdate(), -4)
		ssa.submit()