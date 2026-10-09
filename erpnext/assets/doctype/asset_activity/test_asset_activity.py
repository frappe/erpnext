# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.permissions import add_user_permission

from erpnext.assets.doctype.asset.test_asset import create_asset
from erpnext.buying.test_utils import create_user_with_roles
from erpnext.tests.utils import ERPNextTestSuite


class TestAssetActivity(ERPNextTestSuite):
	def test_user_sees_only_the_activity_of_assets_they_can_read(self):
		computer = create_asset(item_code="Macbook Pro").name
		photocopier = create_asset(item_code="Photocopier").name
		user = "test_asset_activity_restricted@example.com"
		create_user_with_roles(user, "Accounts User")
		add_user_permission("Asset Category", "Computers", user)

		with self.set_user(user):
			assets = frappe.get_list(
				"Asset Activity", filters={"asset": ("in", [computer, photocopier])}, pluck="asset"
			)

		self.assertIn(computer, assets)
		self.assertNotIn(photocopier, assets)
