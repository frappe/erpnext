# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt
import unittest

import frappe

from erpnext.projects.doctype.activity_cost.activity_cost import DuplicationError
from erpnext.setup.doctype.employee.test_employee import make_employee
from erpnext.tests.utils import ERPNextTestSuite


class TestActivityCost(ERPNextTestSuite):
	def test_duplication(self):
		employee = frappe.db.get_all("Employee", filters={"first_name": "_Test Employee"})[0].name
		activity_type = frappe.db.get_all(
			"Activity Type", filters={"activity_type": "_Test Activity Type 1"}
		)[0].name

		activity_cost1 = frappe.new_doc("Activity Cost")
		activity_cost1.update(
			{
				"employee": employee,
				"employee_name": employee,
				"activity_type": activity_type,
				"billing_rate": 100,
				"costing_rate": 50,
			}
		)
		activity_cost1.insert()
		activity_cost2 = frappe.copy_doc(activity_cost1)
		self.assertRaises(DuplicationError, activity_cost2.insert)

	def test_duplication_is_checked_per_employee(self):
		first = make_employee("_test_namesake_1@example.com", "_Test Company", first_name="_Test Namesake")
		second = make_employee("_test_namesake_2@example.com", "_Test Company", first_name="_Test Namesake")
		make_activity_cost(first)
		cost = make_activity_cost(second)

		cost.employee = first
		self.assertRaises(DuplicationError, cost.save)


def make_activity_cost(employee):
	return frappe.get_doc(
		{
			"doctype": "Activity Cost",
			"employee": employee,
			"activity_type": "_Test Activity Type",
			"billing_rate": 100,
			"costing_rate": 50,
		}
	).insert()
