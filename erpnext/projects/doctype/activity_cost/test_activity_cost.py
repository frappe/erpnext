# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt

import frappe

from erpnext.projects.doctype.activity_cost.activity_cost import DuplicationError
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

	def test_default_activity_cost_title_and_duplication(self):
		activity_type = self._activity_type("_Test Default Cost Type")

		default_cost = frappe.get_doc(
			{
				"doctype": "Activity Cost",
				"activity_type": activity_type,
				"billing_rate": 80,
				"costing_rate": 40,
			}
		).insert()
		# without an employee, the title is just the activity type
		self.assertEqual(default_cost.title, activity_type)

		duplicate = frappe.copy_doc(default_cost)
		self.assertRaises(DuplicationError, duplicate.insert)

	def test_employee_name_and_title_are_set(self):
		activity_type = self._activity_type("_Test Employee Cost Type")
		employee = frappe.db.get_all("Employee", filters={"first_name": "_Test Employee"})[0].name
		employee_name = frappe.db.get_value("Employee", employee, "employee_name")

		# employee_name is left blank so set_title has to fetch it
		cost = frappe.get_doc(
			{
				"doctype": "Activity Cost",
				"employee": employee,
				"activity_type": activity_type,
				"billing_rate": 60,
				"costing_rate": 30,
			}
		).insert()
		self.assertEqual(cost.employee_name, employee_name)
		self.assertEqual(cost.title, f"{employee_name} for {activity_type}")

	def _activity_type(self, name):
		if not frappe.db.exists("Activity Type", name):
			frappe.get_doc({"doctype": "Activity Type", "activity_type": name}).insert()
		return name
