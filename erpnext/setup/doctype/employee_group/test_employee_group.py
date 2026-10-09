# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe

from erpnext.crm.doctype.utils import get_scheduled_employees_for_popup
from erpnext.setup.doctype.employee.test_employee import make_employee
from erpnext.tests.utils import ERPNextTestSuite


class TestEmployeeGroup(ERPNextTestSuite):
	def test_duplicate_member(self):
		employee = make_employee("group_duplicate@example.com")
		group = frappe.get_doc(
			{
				"doctype": "Employee Group",
				"employee_group_name": "_Test Duplicate Employee Group",
				"employee_list": [{"employee": employee}, {"employee": employee}],
			}
		)
		with self.assertRaises(frappe.ValidationError):
			group.insert()

	def test_popup_uses_current_active_employee_user(self):
		employee = make_employee("group_member@example.com", first_name="Group", last_name="Member")
		group = frappe.get_doc(
			{
				"doctype": "Employee Group",
				"employee_group_name": "_Test Popup Employee Group",
				"employee_list": [{"employee": employee}],
			}
		).insert()
		self.assertEqual(group.employee_list[0].employee_name, "Group Member")

		# Only replace the timeslot lookup; the member lookup must query the database.
		with patch(
			"erpnext.crm.doctype.utils.frappe.get_all", return_value=[frappe._dict(employee_group=group.name)]
		):
			self.assertEqual(get_scheduled_employees_for_popup("test-medium"), {"group_member@example.com"})

			frappe.db.set_value("Employee", employee, "user_id", "Administrator")
			self.assertEqual(get_scheduled_employees_for_popup("test-medium"), {"Administrator"})

			frappe.db.set_value("Employee", employee, "status", "Left")
			self.assertEqual(get_scheduled_employees_for_popup("test-medium"), set())


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
