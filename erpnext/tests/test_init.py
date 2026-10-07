import unittest

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext import encode_company_abbr, require_permission, require_user_permission
from erpnext.tests.permission_test_utils import (
	MISSING_NAME,
	as_user,
	assert_refused,
	assert_refused_for_names,
	make_fenced_user,
	malformed_names,
)

test_records = frappe.get_test_records("Company")

TEST_USER = "test_init_stock_user@example.com"


def require_warehouse_permission(name):
	require_permission("Warehouse", name)


def require_warehouse_user_permission(name):
	require_user_permission("Warehouse", name)


def name_kwargs(name):
	return {"name": name}


class TestInit(unittest.TestCase):
	def test_encode_company_abbr(self):
		abbr = "NFECT"

		names = [
			"Warehouse Name",
			"ERPNext Foundation India",
			f"Gold - Member - {abbr}",
			f" - {abbr}",
			"ERPNext - Foundation - India",
			f"ERPNext Foundation India - {abbr}",
			f"No-Space-{abbr}",
			"- Warehouse",
		]

		expected_names = [
			f"Warehouse Name - {abbr}",
			f"ERPNext Foundation India - {abbr}",
			f"Gold - Member - {abbr}",
			f" - {abbr}",
			f"ERPNext - Foundation - India - {abbr}",
			f"ERPNext Foundation India - {abbr}",
			f"No-Space-{abbr} - {abbr}",
			f"- Warehouse - {abbr}",
		]

		for i in range(len(names)):
			enc_name = encode_company_abbr(names[i], abbr=abbr)
			self.assertTrue(
				enc_name == expected_names[i],
				f"{enc_name} is not same as {expected_names[i]}",
			)

	def test_translation_files(self):
		from frappe.tests.test_translate import verify_translation_files

		verify_translation_files("erpnext")

	def test_patches(self):
		from frappe.tests.test_patches import check_patch_files

		check_patch_files("erpnext")

	def test_no_unrendered_title_templates(self):
		modules = frappe.get_all("Module Def", filters={"app_name": "erpnext"}, pluck="name")
		for doctype in frappe.get_all("DocType", filters={"module": ("in", modules)}, pluck="name"):
			meta = frappe.get_meta(doctype)
			field = meta.get_field("title")
			if not field or not field.default or "{" not in field.default:
				continue

			self.assertEqual(
				meta.title_field,
				"title",
				f"{doctype}: title default {field.default!r} is stored verbatim because "
				"Document.set_title_field() only renders it when title_field is 'title'",
			)


class TestPermissionHelpers(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_require_permission_refuses_missing_and_malformed_names(self):
		with as_user(make_fenced_user(TEST_USER, ["Stock User"])):
			require_warehouse_permission("Stores - _TC")
			assert_refused_for_names(
				self,
				require_warehouse_permission,
				name_kwargs,
				["", 0, None, ["Stores - _TC"], True],
			)

	def test_require_user_permission_follows_the_fence(self):
		with as_user(make_fenced_user(TEST_USER, ["Stock User"], [("Warehouse", "Stores - _TC")])):
			require_warehouse_user_permission("Stores - _TC")
			assert_refused_for_names(
				self,
				require_warehouse_user_permission,
				name_kwargs,
				["Finished Goods - _TC", ["Stores - _TC"]],
			)

	def test_make_fenced_user_sets_exactly_the_given_roles_and_user_permissions(self):
		make_fenced_user(TEST_USER, ["Stock User", "Projects User"], [("Warehouse", "Stores - _TC")])
		user = make_fenced_user(
			TEST_USER,
			["Stock User"],
			[("Company", "_Test Company"), ("Warehouse", "_Test Warehouse Group - _TC", 1)],
		)

		self.assertEqual(user, TEST_USER)
		self.assertEqual(
			frappe.get_all("Has Role", filters={"parent": TEST_USER, "parenttype": "User"}, pluck="role"),
			["Stock User"],
		)
		user_permissions = []
		for row in frappe.get_all(
			"User Permission",
			filters={"user": TEST_USER},
			fields=["allow", "for_value", "hide_descendants", "apply_to_all_doctypes"],
			order_by="allow asc",
		):
			user_permissions.append(
				(row.allow, row.for_value, row.hide_descendants, row.apply_to_all_doctypes)
			)
		self.assertEqual(
			user_permissions,
			[("Company", "_Test Company", 0, 1), ("Warehouse", "_Test Warehouse Group - _TC", 1, 1)],
		)
		with as_user(user):
			self.assertIn("Stock User", frappe.get_roles())
			self.assertNotIn("Projects User", frappe.get_roles())

	def test_as_user_restores_the_previous_user(self):
		user = make_fenced_user(TEST_USER, ["Stock User"])
		previous = frappe.session.user

		with as_user(user) as current:
			self.assertEqual(current, user)
			self.assertEqual(frappe.session.user, user)
		self.assertEqual(frappe.session.user, previous)

		with self.assertRaises(frappe.ValidationError):
			with as_user(user):
				frappe.throw("_Test as_user failure")
		self.assertEqual(frappe.session.user, previous)

	def test_assert_refused_for_names_covers_the_malformed_names(self):
		seen = []

		def refuse(name):
			seen.append(name)
			frappe.throw(frappe._("Not permitted"), frappe.PermissionError)

		assert_refused_for_names(self, refuse, name_kwargs, ["_Test Forbidden"])

		expected = ["_Test Forbidden"]
		for name in malformed_names():
			expected.append(name)
		self.assertEqual(seen, expected)
		self.assertIn(MISSING_NAME, seen)
		with self.assertRaises(AssertionError):
			assert_refused(self, frappe.throw, "_Test not a permission error", frappe.PermissionError)
