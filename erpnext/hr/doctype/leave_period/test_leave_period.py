# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe, erpnext
import unittest
from frappe.utils import today, add_months
from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.hr.doctype.leave_application.leave_application import get_leave_balance_on

test_dependencies = ["Employee", "Leave Type", "Leave Policy"]

class TestLeavePeriod(unittest.TestCase):
	def setUp(self):
		frappe.db.sql("delete from `tabLeave Period`")

	def test_leave_grant(self):
		leave_type = "_Test Leave Type"

		# create the leave policy
		leave_policy = frappe.get_doc({
			"doctype": "Leave Policy",
			"leave_policy_details": [{
				"leave_type": leave_type,
				"annual_allocation": 20
			}]
		}).insert()
		leave_policy.submit()

		# create employee and assign the leave period
		employee = "test_leave_period@employee.com"
		employee_doc_name = make_employee(employee)
		frappe.db.set_value("Employee", employee_doc_name, "leave_policy", leave_policy.name)

		# clear the already allocated leave
		frappe.db.sql('''delete from `tabLeave Allocation` where employee=%s''', "test_leave_period@employee.com")

		# create the leave period
		leave_period = create_leave_period(add_months(today(), -3), add_months(today(), 3))

		# test leave_allocation
		leave_period.grant_leave_allocation(employee=employee_doc_name)
		self.assertEqual(get_leave_balance_on(employee_doc_name, leave_type, today()), 20)

def create_leave_period(from_date, to_date):
	leave_period = frappe.get_doc({
		"doctype": "Leave Period",
		"company": erpnext.get_default_company(),
		"from_date": from_date,
		"to_date": to_date,
		"is_active": 1
	}).insert()
	return leave_period