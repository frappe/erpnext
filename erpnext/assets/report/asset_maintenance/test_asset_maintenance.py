# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.buying.test_utils import create_user_with_roles
from erpnext.tests.utils import ERPNextTestSuite


class TestAssetMaintenanceReport(ERPNextTestSuite):
	def test_maintenance_roles_can_open_the_report_and_read_its_data(self):
		for role in ("Quality Manager", "Manufacturing User"):
			user = f"test_asset_maintenance_{frappe.scrub(role)}@example.com"
			create_user_with_roles(user, role)
			with self.set_user(user):
				self.assertTrue(frappe.has_permission("Report", "read", "Asset Maintenance"))
				self.assertTrue(frappe.has_permission("Asset Maintenance", "read"))
