import frappe

from erpnext import (
	_is_permitted,
	_is_within_user_permissions,
	encode_company_abbr,
	require_party_permission,
	require_permission,
	require_user_permission,
)
from erpnext.tests.permission_test_utils import (
	MISSING_NAME,
	as_user,
	assert_not_found,
	assert_refused,
	assert_refused_for_names,
	assert_refused_without,
	make_fenced_user,
	malformed_names,
)
from erpnext.tests.utils import ERPNextTestSuite

TEST_USER = "test_init_stock_user@example.com"
SALES_USER = "test_init_sales_user@example.com"
SENTINEL = {"message": "_Test Init Sentinel"}


def name_kwargs(name):
	return {"name": name}


def silent_names():
	names = ["", 0, False, None, {}, [], ["Stores - _TC"]]
	for name in malformed_names():
		names.append(name)
	return names


class TestInit(ERPNextTestSuite):
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

	def assert_silent_check(self, check, allowed, denied):
		frappe.local.message_log = [SENTINEL]
		self.assertTrue(check("Warehouse", allowed))
		names = [denied]
		for name in silent_names():
			names.append(name)
		for name in names:
			self.assertFalse(check("Warehouse", name))
		self.assertEqual(frappe.local.message_log, [SENTINEL])
		frappe.local.message_log = []

	def is_readable(self, doctype, name):
		return _is_permitted(doctype, name, "read")

	def test_is_permitted_is_silent_and_refuses_missing_and_malformed_names(self):
		with as_user(make_fenced_user(TEST_USER, ["Stock User"], [("Warehouse", "Stores - _TC")])):
			self.assert_silent_check(self.is_readable, "Stores - _TC", "Finished Goods - _TC")
			self.assertFalse(_is_permitted("Warehouse", "Stores - _TC", "delete"))

	def test_is_within_user_permissions_is_silent_and_follows_the_fence(self):
		with as_user(make_fenced_user(TEST_USER, ["Stock User"], [("Warehouse", "Stores - _TC")])):
			self.assert_silent_check(_is_within_user_permissions, "Stores - _TC", "Finished Goods - _TC")

		with as_user(make_fenced_user(TEST_USER, ["Stock User"], [("Company", "_Test Company")])):
			self.assertTrue(_is_within_user_permissions("Warehouse", "Finished Goods - _TC"))
			self.assertFalse(_is_within_user_permissions("Warehouse", "Stores - _TC3"))

	def test_require_permission_and_require_user_permission_refuse_with_the_constant(self):
		with as_user(make_fenced_user(TEST_USER, ["Stock User"], [("Warehouse", "Stores - _TC")])):
			require_permission("Warehouse", "Stores - _TC")
			require_user_permission("Warehouse", "Stores - _TC")
			names = ["Finished Goods - _TC"]
			for name in silent_names():
				names.append(name)
			for name in names:
				assert_refused(self, require_permission, "Warehouse", name)
				assert_refused(self, require_user_permission, "Warehouse", name)

	def test_require_party_permission_refuses_bad_types_missing_and_forbidden_parties(self):
		user = make_fenced_user(SALES_USER, ["Sales User"], [("Customer", "_Test Customer")])

		with as_user(user):
			require_party_permission("Customer", "_Test Customer")
			for party in ("", None):
				self.assertIsNone(require_party_permission("Customer", party))
			for party_type in ("Warehouse", MISSING_NAME, None, "", {"name": ["like", "%"]}, ["Customer"]):
				assert_refused(self, require_party_permission, party_type, "_Test Customer")
			assert_refused(self, require_party_permission, "Customer", "_Test Customer 1")
			for party in (
				MISSING_NAME,
				0,
				False,
				{},
				[],
				{"name": ["like", "%"]},
				["like", "%"],
				["_Test Customer"],
			):
				assert_not_found(self, require_party_permission, "Customer", party)

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
			if name == MISSING_NAME or not isinstance(name, str):
				raise frappe.DoesNotExistError
			frappe.throw_permission_error()

		def refuse_everything(name):
			frappe.throw_permission_error()

		assert_refused_for_names(self, refuse, name_kwargs, ["_Test Forbidden"], caller_supplied=True)

		expected = ["_Test Forbidden"]
		for name in malformed_names():
			expected.append(name)
		self.assertEqual(seen, expected)
		self.assertIn(MISSING_NAME, seen)
		with self.assertRaises(AssertionError):
			assert_refused(self, frappe.throw, "_Test not a permission error", frappe.PermissionError)

		assert_refused_for_names(self, refuse_everything, name_kwargs, ["_Test Forbidden"])
		with self.assertRaises(frappe.PermissionError):
			assert_refused_for_names(self, refuse_everything, name_kwargs, [], caller_supplied=True)
		with self.assertRaises(frappe.DoesNotExistError):
			assert_refused_for_names(self, refuse, name_kwargs, [])

	def test_assert_refused_without_fails_when_a_hidden_value_reaches_the_message_log(self):
		def refuse_quietly():
			frappe.throw_permission_error()

		def refuse_loudly():
			frappe.msgprint("linked to _Test Hidden Company")
			frappe.throw_permission_error()

		assert_refused_without(self, ["_Test Hidden Company"], refuse_quietly)
		with self.assertRaises(AssertionError):
			assert_refused_without(self, ["_Test Hidden Company"], refuse_loudly)
		with self.assertRaises(AssertionError):
			assert_refused(self, refuse_loudly)
		frappe.local.message_log = []
