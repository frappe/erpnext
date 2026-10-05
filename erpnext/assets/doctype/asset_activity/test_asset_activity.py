# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.assets.doctype.asset.test_asset import create_asset
from erpnext.tests.utils import ERPNextTestSuite


class TestAssetActivity(ERPNextTestSuite):
	def test_draft_asset_can_be_deleted(self):
		asset = create_asset()
		self.assertTrue(frappe.db.exists("Asset Activity", {"asset": asset.name}))

		frappe.delete_doc("Asset", asset.name)

		self.assertFalse(frappe.db.exists("Asset", asset.name))
		subjects = frappe.get_all("Asset Activity", {"asset": asset.name}, pluck="subject")
		self.assertIn("Asset deleted", subjects)
