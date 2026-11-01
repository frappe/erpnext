# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.permissions import add_user_permission

from erpnext.assets.doctype.asset.test_asset import create_asset
from erpnext.assets.doctype.asset_maintenance.test_asset_maintenance import get_maintenance_tasks
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

	def test_user_restricted_to_a_category_sees_only_its_maintenance(self):
		computers = make_asset_maintenance("Macbook Pro")
		equipment = make_asset_maintenance("Photocopier")
		user = "test_asset_maintenance_category@example.com"
		create_user_with_roles(user, "Quality Manager")
		add_user_permission("Asset Category", "Computers", user)

		with self.set_user(user):
			visible = frappe.get_list("Asset Maintenance", pluck="name")

		self.assertIn(computers, visible)
		self.assertNotIn(equipment, visible)


def make_asset_maintenance(item_code: str) -> str:
	asset = create_asset(item_code=item_code, maintenance_required=1)
	return (
		frappe.get_doc(
			{
				"doctype": "Asset Maintenance",
				"asset_name": asset.name,
				"maintenance_team": "Team Awesome",
				"company": "_Test Company",
				"asset_maintenance_tasks": get_maintenance_tasks(),
			}
		)
		.insert()
		.name
	)
