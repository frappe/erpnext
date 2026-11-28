# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from copy import deepcopy
from unittest.mock import patch

import frappe
from frappe.client import get, get_list
from frappe.modules.utils import sync_customizations_for_doctype
from frappe.permissions import reset_perms, setup_custom_perms
from frappe.utils.nestedset import get_root_of
from frappe.utils.print_format import download_pdf
from frappe.www.printview import get_context, validate_print_permission

from erpnext.setup.doctype.territory.territory import restrict_customer_territory_permissions
from erpnext.tests.permission_test_utils import make_fenced_user
from erpnext.tests.utils import ERPNextTestSuite


class TestTerritory(ERPNextTestSuite):
	def setUp(self):
		reset_perms("Territory")
		frappe.clear_cache(doctype="Territory")
		self.customer = make_fenced_user("territory-customer@example.com", ["Customer"])
		self.portal_user = make_fenced_user("territory-portal@example.com", [])
		self.sales_user = make_fenced_user("territory-sales@example.com", ["Sales User"])
		self.customer_sales_user = make_fenced_user(
			"territory-customer-sales@example.com", ["Customer", "Sales User"]
		)
		fiscal_year = frappe.get_doc(
			doctype="Fiscal Year",
			year="_Test Territory Permissions 2196",
			year_start_date="2196-01-01",
			year_end_date="2196-12-31",
		).insert()
		distribution = frappe.get_doc(
			doctype="Monthly Distribution", distribution_id="_Test Territory Permissions"
		)
		distribution.get_months()
		distribution.insert()
		self.manager = frappe.get_doc(
			doctype="Sales Person", sales_person_name="_Test Territory Private Manager", enabled=1
		).insert()
		self.territory = frappe.get_doc(
			doctype="Territory",
			territory_name="_Test Territory Private Targets",
			territory_manager=self.manager.name,
			targets=[
				{
					"fiscal_year": fiscal_year.name,
					"distribution_id": distribution.name,
					"target_amount": 717171.05,
				}
			],
		).insert()

	def tearDown(self):
		super().tearDown()
		frappe.clear_cache(doctype="Territory")
		for user in (self.customer, self.portal_user, self.sales_user, self.customer_sales_user):
			frappe.clear_cache(user=user)

	def test_root_tree_records_can_be_saved(self):
		for doctype in ("Territory", "Customer Group", "Supplier Group", "Sales Person"):
			with self.subTest(doctype=doctype):
				root = frappe.get_doc(doctype, get_root_of(doctype))
				root.save()
				self.assertFalse(root.get(root.nsm_parent_field))

	def test_customer_can_select_names_without_reading_internal_fields(self):
		with self.set_user(self.customer):
			self.assertEqual(frappe.get_cached_value("User", self.customer, "user_type"), "Website User")
			self.assertEqual(
				get_list("Territory", filters={"name": self.territory.name}),
				[{"name": self.territory.name}],
			)
			self.assertRaises(frappe.PermissionError, get, "Territory", self.territory.name)
			self.assertEqual(
				get_list(
					"Territory",
					fields=["name", "targets.target_amount"],
					filters={"name": self.territory.name},
				),
				[{"name": self.territory.name}],
			)

	def test_customer_cannot_print_internal_fields(self):
		with self.set_user(self.customer):
			for method, args in (
				(validate_print_permission, (self.territory,)),
				(self.print_context, ()),
				(download_pdf, ("Territory", self.territory.name)),
			):
				with self.subTest(method=method.__name__), patch("frappe.get_print") as render_pdf:
					with self.assertRaises(frappe.PermissionError) as error:
						method(*args)
					self.assertNotIn(self.manager.name, str(error.exception))
					self.assertNotIn("717171", str(error.exception))
					render_pdf.assert_not_called()

	def test_customer_has_no_output_or_sharing_permissions(self):
		with self.set_user(self.customer):
			for ptype in ("print", "email", "export", "report", "share"):
				with self.subTest(ptype=ptype):
					self.assertFalse(frappe.has_permission("Territory", ptype, self.territory))

	def test_sales_roles_can_print_internal_fields(self):
		for user in (self.sales_user, self.customer_sales_user):
			with self.subTest(user=user), self.set_user(user):
				self.assertEqual(get("Territory", self.territory.name)["name"], self.territory.name)
				body = self.print_context()["body"]
				self.assertIn(self.manager.name, body)
				self.assertIn(self.territory.targets[0].get_formatted("target_amount"), body)

	def test_unrelated_portal_user_cannot_print(self):
		with self.set_user(self.portal_user):
			self.assertRaises(frappe.PermissionError, self.print_context)

	def test_document_share_authorizes_only_the_shared_territory(self):
		other = frappe.get_doc(doctype="Territory", territory_name="_Test Territory Not Shared").insert()
		frappe.share.add("Territory", self.territory.name, self.portal_user, notify=0)
		with self.set_user(self.portal_user):
			self.assertIn(self.manager.name, self.print_context()["body"])
			self.assertRaises(frappe.PermissionError, validate_print_permission, other)

	def test_permission_cleanup_corrects_legacy_custom_rule_and_is_idempotent(self):
		legacy = self.make_legacy_customer_rule()
		before = self.territory.as_dict()
		self.assertEqual(legacy.print, 1)
		restrict_customer_territory_permissions()
		after_first_cleanup = legacy.reload().modified
		restrict_customer_territory_permissions()
		legacy.reload()
		self.assertEqual(legacy.modified, after_first_cleanup)
		self.assertEqual(legacy.select, 1)
		for ptype in ("print", "email", "export", "report", "share"):
			self.assertEqual(legacy.get(ptype), 0)
		with self.set_user(self.customer):
			self.assertRaises(frappe.PermissionError, self.print_context)
			self.assertEqual(
				get_list("Territory", filters={"name": self.territory.name}), [{"name": self.territory.name}]
			)
		self.assertEqual(self.territory.reload().as_dict(), before)

	def test_permission_cleanup_preserves_explicit_read_and_other_roles(self):
		legacy = self.make_legacy_customer_rule()
		read_rule = frappe.copy_doc(legacy)
		read_rule.update({"read": 1, "if_owner": 1})
		read_rule.insert()
		preserved = frappe.get_all(
			"Custom DocPerm", filters={"parent": "Territory", "name": ["!=", legacy.name]}, fields=["*"]
		)
		restrict_customer_territory_permissions()
		self.assertEqual(
			frappe.get_all(
				"Custom DocPerm", filters={"parent": "Territory", "name": ["!=", legacy.name]}, fields=["*"]
			),
			preserved,
		)
		self.assertEqual(legacy.reload().print, 0)

	def test_permission_cleanup_does_not_restore_selection(self):
		legacy = self.make_legacy_customer_rule()
		legacy.select = 0
		legacy.save()
		restrict_customer_territory_permissions()
		self.assertEqual(legacy.reload().select, 0)
		self.assertEqual(legacy.print, 0)

	def test_permission_cleanup_does_not_create_missing_customer_rule(self):
		legacy = self.make_legacy_customer_rule()
		frappe.delete_doc("Custom DocPerm", legacy.name)
		restrict_customer_territory_permissions()
		self.assertFalse(frappe.db.exists("Custom DocPerm", {"parent": "Territory", "role": "Customer"}))

	def test_permission_cleanup_does_not_customize_default_permissions(self):
		restrict_customer_territory_permissions()
		self.assertFalse(frappe.db.exists("Custom DocPerm", {"parent": "Territory"}))

	def test_migration_restricts_customer_permissions_after_each_customization_sync(self):
		legacy = self.make_legacy_customer_rule()
		customization = {
			"doctype": "Territory",
			"custom_fields": [],
			"property_setters": [],
			"custom_perms": frappe.get_all("Custom DocPerm", filters={"parent": "Territory"}, fields=["*"]),
		}
		permission_fields = ("select", "read", "print", "email", "export", "report", "share")

		for migration in (1, 2):
			with self.subTest(migration=migration):
				sync_customizations_for_doctype(deepcopy(customization), "")
				for hook in frappe.get_hooks("after_migrate", app_name="erpnext"):
					frappe.get_attr(hook)()
				self.assertEqual(
					frappe.db.get_value("Custom DocPerm", legacy.name, permission_fields),
					(1, 0, 0, 0, 0, 0, 0),
				)

	def print_context(self):
		with patch.object(
			frappe.local,
			"form_dict",
			frappe._dict(doctype="Territory", name=self.territory.name, no_letterhead=1),
		):
			return get_context({})

	@staticmethod
	def make_legacy_customer_rule():
		setup_custom_perms("Territory")
		rule = frappe.get_doc("Custom DocPerm", {"parent": "Territory", "role": "Customer", "permlevel": 0})
		rule.update({"read": 0, "select": 1, "print": 1, "email": 1, "export": 1, "report": 1, "share": 1})
		rule.save()
		return rule
