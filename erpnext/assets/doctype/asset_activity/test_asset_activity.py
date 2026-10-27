# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.permissions import add_user_permission
from frappe.tests.utils import FrappeTestCase

from erpnext.assets.doctype.asset.test_asset import create_asset
from erpnext.assets.doctype.asset_activity.asset_activity import add_asset_activity
from erpnext.assets.doctype.asset_maintenance.test_asset_maintenance import (
	create_asset_data as create_photocopier_data,
)


class TestAssetActivity(FrappeTestCase):
	def test_user_sees_only_the_activity_of_assets_they_can_read(self):
		create_photocopier_data()
		computer = create_asset(item_code="Macbook Pro").name
		photocopier = create_asset(item_code="Photocopier", asset_category="Equipment").name
		for asset in (computer, photocopier):
			add_asset_activity(asset, "Asset created")

		user = create_user_with_roles("test_asset_activity_restricted@example.com", "Accounts User")
		add_user_permission("Asset Category", "Computers", user)

		with self.set_user(user):
			assets = frappe.get_list(
				"Asset Activity", filters={"asset": ("in", [computer, photocopier])}, pluck="asset"
			)

		self.assertIn(computer, assets)
		self.assertNotIn(photocopier, assets)


def create_user_with_roles(email: str, *roles: str) -> str:
	if not frappe.db.exists("User", email):
		frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@", 1)[0]}).insert(
			ignore_permissions=True
		)
	user = frappe.get_doc("User", email)
	user.add_roles(*roles)
	return email
