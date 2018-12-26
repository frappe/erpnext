# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals
from erpnext.hr.doctype.employee.test_employee import make_employee

import frappe
import unittest
class TestEmployeeGroup(unittest.TestCase):
	
	def test_employee_group(self):
		test_make_employee_group = make_employee_group()
		test_get_employee_group = get_employee_group()
		self.assertEquals(test_make_employee_group, test_get_employee_group)

def make_employee_group():
	employee = make_employee("testemployee@example.com")
	employee_group = frappe.get_doc({
		"doctype": "Employee Group",
		"employee_group_name": "_Test Employee Group",
		"employee_list": [
			{
				"employee": employee
			}
		]
	})
	employee_group_exist = frappe.db.exists("Employee Group", "_Test Employee Group")
	if not employee_group_exist:
		employee_group.insert()
		return employee_group.employee_group_name
	else:
		return employee_group_exist

def get_employee_group():
	employee_group = frappe.db.exists("Employee Group", "_Test Employee Group")
	return employee_group