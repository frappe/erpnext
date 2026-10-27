# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe


class TestDriver(unittest.TestCase):
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
