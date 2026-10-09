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

	def test_employee_user_sync_and_manual_user(self):
		user = f"driver-{frappe.generate_hash(length=10)}@example.com"
		employee = make_employee(user, company="_Test Company")
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

	def test_employee_change_only_clears_inherited_user(self):
		user = "driver-original@example.com"
		employee = make_employee(user, company="_Test Company")
		replacement = make_employee("driver-replacement@example.com", company="_Test Company")
		frappe.db.set_value("Employee", replacement, "user_id", None)

		cases = (
			(replacement, user, None, None),
			(None, user, "Administrator", "Administrator"),
			(replacement, None, None, "Administrator"),
			(None, None, None, "Administrator"),
		)
		for new_employee, employee_user, replacement_user, expected_user in cases:
			with self.subTest(new_employee=new_employee, employee_user=employee_user):
				frappe.db.set_value("Employee", employee, "user_id", employee_user)
				driver = frappe.get_doc(
					{
						"doctype": "Driver",
						"full_name": "Test Driver",
						"status": "Active",
						"employee": employee,
						"user": "Administrator",
					}
				).insert()
				driver.employee = new_employee
				if replacement_user:
					driver.user = replacement_user
				driver.save()
				self.assertEqual(driver.user, expected_user)
