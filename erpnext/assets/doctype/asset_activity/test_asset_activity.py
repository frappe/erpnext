# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.assets.doctype.asset.test_asset import create_asset
from erpnext.tests.utils import ERPNextTestSuite


class TestAssetActivity(ERPNextTestSuite):
	def test_deleting_draft_asset_removes_its_activity(self):
		asset = create_asset()
		self.assertTrue(frappe.db.exists("Asset Activity", {"asset": asset.name}))

		frappe.delete_doc("Asset", asset.name)

		self.assertFalse(frappe.db.exists("Asset", asset.name))
		self.assertFalse(frappe.db.exists("Asset Activity", {"asset": asset.name}))

		reused = create_asset(do_not_save=True)
		reused.name = asset.name
		reused.flags.name_set = True
		reused.insert()
		self.assertEqual(reused.name, asset.name)

		subjects = frappe.get_all("Asset Activity", {"asset": reused.name}, pluck="subject")
		self.assertEqual(subjects, ["Asset created"])
