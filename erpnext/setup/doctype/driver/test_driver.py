# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.setup.doctype.employee.test_employee import make_employee
from erpnext.tests.utils import ERPNextTestSuite


class TestDriver(ERPNextTestSuite):
	def test_expiry_cannot_precede_issuing_date(self):
		driver = frappe.get_doc(
			{
				"doctype": "Driver",
				"full_name": "Test Driver",
				"status": "Active",
				"issuing_date": "2025-01-01",
				"expiry_date": "2020-01-01",
			}
		)
		with self.assertRaises(frappe.ValidationError):
			driver.insert()

	def test_fleet_manager_can_maintain_drivers(self):
		user = f"fleet-{frappe.generate_hash(length=10)}@example.com"
		frappe.get_doc(
			{"doctype": "User", "email": user, "first_name": "Fleet", "send_welcome_email": 0}
		).insert().add_roles("Fleet Manager")
		for permission in ("create", "write", "delete"):
			self.assertTrue(frappe.has_permission("Driver", permission, user=user))

	def test_employee_user_sync_and_manual_user(self):
		user = f"driver-{frappe.generate_hash(length=10)}@example.com"
		employee = make_employee(user)
		driver = frappe.get_doc(
			{"doctype": "Driver", "full_name": "Test Driver", "status": "Active", "employee": employee}
		).insert()
		self.assertEqual(driver.user, user)

		driver.employee = None
		driver.save()
		self.assertFalse(driver.user)

		frappe.db.set_value("Employee", employee, "user_id", None)
		driver.user = "Administrator"
		driver.employee = employee
		driver.save()
		self.assertEqual(driver.user, "Administrator")
