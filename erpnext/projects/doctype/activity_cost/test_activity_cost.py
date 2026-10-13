# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.projects.doctype.activity_cost.activity_cost import DuplicationError
from erpnext.setup.doctype.employee.test_employee import make_employee


class TestActivityCost(FrappeTestCase):
	def test_duplication(self):
		frappe.db.sql("delete from `tabActivity Cost`")
		activity_cost1 = frappe.new_doc("Activity Cost")
		activity_cost1.update(
			{
				"employee": "_T-Employee-00001",
				"employee_name": "_Test Employee",
				"activity_type": "_Test Activity Type 1",
				"billing_rate": 100,
				"costing_rate": 50,
			}
		)
		activity_cost1.insert()
		activity_cost2 = frappe.copy_doc(activity_cost1)
		self.assertRaises(DuplicationError, activity_cost2.insert)
		frappe.db.sql("delete from `tabActivity Cost`")

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
