# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestAssetMaintenanceReport(FrappeTestCase):
	def test_maintenance_roles_can_open_the_report_and_read_its_data(self):
		for role in ("Quality Manager", "Manufacturing User"):
			user = f"test_asset_maintenance_{frappe.scrub(role)}@example.com"
			create_user_with_roles(user, role)
			with self.set_user(user):
				self.assertTrue(frappe.get_doc("Report", "Asset Maintenance").is_permitted())
				self.assertTrue(frappe.has_permission("Asset Maintenance", "read"))


def create_user_with_roles(email: str, *roles: str):
	if not frappe.db.exists("User", email):
		frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@")[0]}).insert()
	frappe.get_doc("User", email).add_roles(*roles)
