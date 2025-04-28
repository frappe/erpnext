# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
<<<<<<< HEAD
import unittest

import frappe
from frappe.tests import IntegrationTestCase
=======

import unittest

import frappe
>>>>>>> 7c4cf3e834 (Favicon.svg)

from erpnext.setup.doctype.employee.test_employee import make_employee


<<<<<<< HEAD
class TestEmployeeGroup(IntegrationTestCase):
=======
class TestEmployeeGroup(unittest.TestCase):
>>>>>>> 7c4cf3e834 (Favicon.svg)
	pass


def make_employee_group():
	employee = make_employee("testemployee@example.com")
	employee_group = frappe.get_doc(
		{
			"doctype": "Employee Group",
			"employee_group_name": "_Test Employee Group",
			"employee_list": [{"employee": employee}],
		}
	)
	employee_group_exist = frappe.db.exists("Employee Group", "_Test Employee Group")
	if not employee_group_exist:
		employee_group.insert()
		return employee_group.employee_group_name
	else:
		return employee_group_exist


def get_employee_group():
	employee_group = frappe.db.exists("Employee Group", "_Test Employee Group")
	return employee_group
