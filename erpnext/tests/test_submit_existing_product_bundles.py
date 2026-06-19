# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.patches.v16_0.submit_existing_product_bundles import execute
from erpnext.selling.doctype.product_bundle.product_bundle import get_active_product_bundle
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.tests.utils import ERPNextTestSuite


class TestSubmitExistingProductBundles(ERPNextTestSuite):
	def _make_legacy_bundle(self, item_code, child, disabled=0):
		"""Recreate the pre-migration shape: a draft bundle named after its parent item."""
		bundle = frappe.get_doc(
			{
				"doctype": "Product Bundle",
				"new_item_code": item_code,
				"items": [{"item_code": child, "qty": 1}],
			}
		).insert()
		# revert to the legacy state: name == item_code, draft
		frappe.rename_doc("Product Bundle", bundle.name, item_code, force=True, show_alert=False)
		frappe.db.set_value(
			"Product Bundle", item_code, {"docstatus": 0, "disabled": disabled}, update_modified=False
		)
		return item_code

	def test_patch_renames_and_submits_legacy_bundle(self):
		parent = make_item("_Test Patch PB Parent", {"is_stock_item": 0, "is_sales_item": 1}).name
		child = make_item("_Test Patch PB Child", {"is_stock_item": 1}).name
		legacy = self._make_legacy_bundle(parent, child)

		execute()

		# legacy name is gone; an active versioned bundle now resolves for the item
		self.assertFalse(frappe.db.exists("Product Bundle", legacy))
		migrated = get_active_product_bundle(parent)
		self.assertTrue(migrated and migrated.startswith("PB-"))
		self.assertEqual(frappe.db.get_value("Product Bundle", migrated, "docstatus"), 1)
		self.assertEqual(frappe.db.get_value("Product Bundle", migrated, "is_active"), 1)

	def test_patch_seeds_is_active_from_disabled(self):
		parent = make_item("_Test Patch PB Disabled Parent", {"is_stock_item": 0, "is_sales_item": 1}).name
		child = make_item("_Test Patch PB Disabled Child", {"is_stock_item": 1}).name
		self._make_legacy_bundle(parent, child, disabled=1)

		execute()

		# a disabled legacy bundle becomes submitted but inactive
		self.assertIsNone(get_active_product_bundle(parent))
		migrated = frappe.db.get_value("Product Bundle", {"new_item_code": parent, "docstatus": 1}, "name")
		self.assertTrue(migrated and migrated.startswith("PB-"))
		self.assertEqual(frappe.db.get_value("Product Bundle", migrated, "is_active"), 0)

	def test_patch_submits_partially_migrated_bundle(self):
		"""An interrupted run can leave a bundle renamed (PB-*) but still a draft;
		re-running the patch must submit it rather than skip it."""
		parent = make_item("_Test Patch PB Partial Parent", {"is_stock_item": 0, "is_sales_item": 1}).name
		child = make_item("_Test Patch PB Partial Child", {"is_stock_item": 1}).name

		# a freshly inserted (unsubmitted) bundle is already PB-named: exactly the
		# renamed-but-not-submitted state of an interrupted migration
		bundle = frappe.get_doc(
			{
				"doctype": "Product Bundle",
				"new_item_code": parent,
				"items": [{"item_code": child, "qty": 1}],
			}
		).insert()
		self.assertTrue(bundle.name.startswith("PB-"))
		self.assertEqual(bundle.docstatus, 0)

		execute()

		self.assertEqual(get_active_product_bundle(parent), bundle.name)
		self.assertEqual(frappe.db.get_value("Product Bundle", bundle.name, "docstatus"), 1)
