# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestLedgerHealthMonitor(ERPNextTestSuite):
	def test_enabled_monitor_needs_a_company(self):
		def save(enabled, companies):
			monitor = frappe.get_doc("Ledger Health Monitor")
			monitor.enable_health_monitor = enabled
			monitor.set("companies", [{"company": company} for company in companies])
			monitor.save()

		self.assertRaisesRegex(frappe.ValidationError, "at least one Company", save, 1, [])
		save(1, ["_Test Company"])
		save(0, [])

	def test_monitor_and_results_permissions(self):
		self.assertFalse(
			frappe.permissions.has_permission(
				"Ledger Health Monitor", "write", user=self.make_user("Accounts User")
			)
		)
		self.assertTrue(
			frappe.permissions.has_permission(
				"Ledger Health Monitor", "write", user=self.make_user("Accounts Manager")
			)
		)
		self.assertTrue(
			frappe.permissions.has_permission(
				"Ledger Health", "read", user=self.make_user("Accounts Manager")
			)
		)
		self.assertFalse(
			frappe.permissions.has_permission("Ledger Health", "read", user=self.make_user("Accounts User"))
		)
		self.assertFalse(
			frappe.permissions.has_permission(
				"Ledger Health", "write", user=self.make_user("Accounts Manager")
			)
		)

	def make_user(self, role):
		email = f"lhm-{frappe.scrub(role)}@example.com"
		if not frappe.db.exists("User", email):
			user = frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": role, "send_welcome_email": 0}
			).insert(ignore_permissions=True)
			user.add_roles(role)
		return email
