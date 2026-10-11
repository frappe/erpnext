import frappe
from frappe.permissions import setup_custom_perms
from frappe.tests.utils import FrappeTestCase

from erpnext.patches.v16_0 import (
	mirror_release_perms_to_custom_docperm,
	remove_all_role_from_payment_terms_template,
)
from erpnext.setup.install import grant_address_read_to_accounts_manager
from erpnext.tests.permission_test_utils import insert_test_record

FLAGS = (
	"select",
	"read",
	"write",
	"create",
	"delete",
	"submit",
	"cancel",
	"amend",
	"report",
	"export",
	"import",
	"share",
	"print",
	"email",
)


class TestPermissionPatches(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()
		for doctype in ("Payment Terms Template", "POS Invoice", "Serial and Batch Bundle", "Address"):
			frappe.clear_cache(doctype=doctype)

	def level_zero_rules(self, doctype, role):
		return frappe.get_all(
			"Custom DocPerm",
			filters={"parent": doctype, "role": role, "permlevel": 0},
			fields=["name", "if_owner", *FLAGS],
		)

	def set_only(self, doctype, role, granted):
		values = {}
		for flag in FLAGS:
			values[flag] = 1 if flag in granted else 0
		for rule in self.level_zero_rules(doctype, role):
			frappe.db.set_value("Custom DocPerm", rule.name, values)

	def insert_rule(self, doctype, role, granted):
		values = {"parent": doctype, "parenttype": "DocType", "parentfield": "permissions", "role": role}
		for flag in FLAGS:
			values[flag] = 1 if flag in granted else 0
		insert_test_record("Custom DocPerm", values)

	def test_mirror_adds_the_release_rules_to_a_customised_doctype(self):
		setup_custom_perms("Payment Terms Template")
		roles = mirror_release_perms_to_custom_docperm.GRANTS["Payment Terms Template"]
		for role in roles:
			frappe.db.delete("Custom DocPerm", {"parent": "Payment Terms Template", "role": role})
		mirror_release_perms_to_custom_docperm.execute()
		for role, ptypes in roles.items():
			rules = self.level_zero_rules("Payment Terms Template", role)
			self.assertEqual(len(rules), 1, role)
			for ptype in ptypes:
				self.assertEqual(rules[0][ptype], 1, role)

	def test_mirror_widens_an_unedited_copy_of_the_previous_release(self):
		setup_custom_perms("POS Invoice")
		self.set_only("POS Invoice", "Sales User", ("select",))
		mirror_release_perms_to_custom_docperm.execute()
		rules = self.level_zero_rules("POS Invoice", "Sales User")
		self.assertEqual(len(rules), 1)
		self.assertEqual(rules[0].select, 1)
		self.assertEqual(rules[0].read, 1)

	def test_mirror_leaves_an_admin_changed_rule_alone(self):
		setup_custom_perms("POS Invoice")
		self.set_only("POS Invoice", "Sales Manager", ("select", "print"))
		mirror_release_perms_to_custom_docperm.execute()
		rules = self.level_zero_rules("POS Invoice", "Sales Manager")
		self.assertEqual(len(rules), 1)
		self.assertEqual(rules[0].read, 0)
		self.assertEqual(rules[0].print, 1)

	def test_remove_all_rule_deletes_every_level_zero_all_rule(self):
		setup_custom_perms("Payment Terms Template")
		self.insert_rule(
			"Payment Terms Template", "All", ("select", "report", "export", "print", "email", "share")
		)
		self.insert_rule("Payment Terms Template", "All", ("read",))
		remove_all_role_from_payment_terms_template.execute()
		self.assertFalse(self.level_zero_rules("Payment Terms Template", "All"))
		self.assertTrue(self.level_zero_rules("Payment Terms Template", "Sales User"))

	def test_remove_all_rule_skips_a_doctype_that_is_not_customised(self):
		frappe.db.delete("Custom DocPerm", {"parent": "Payment Terms Template"})
		remove_all_role_from_payment_terms_template.execute()
		self.assertFalse(frappe.db.exists("Custom DocPerm", {"parent": "Payment Terms Template"}))

	def address_rules_except_accounts_manager(self):
		rules = []
		for rule in frappe.get_all(
			"Custom DocPerm",
			filters={"parent": "Address", "role": ("!=", "Accounts Manager")},
			fields=["role", "permlevel", "if_owner", *FLAGS],
			order_by="role, permlevel, if_owner",
		):
			rules.append(rule)
		return rules

	def shipped_address_rules(self):
		rules = []
		for rule in frappe.get_all(
			"DocPerm",
			filters={"parent": "Address", "role": ("!=", "Accounts Manager")},
			fields=["role", "permlevel", "if_owner", *FLAGS],
			order_by="role, permlevel, if_owner",
		):
			rules.append(rule)
		return rules

	def test_address_grant_is_idempotent_and_keeps_other_roles(self):
		frappe.db.delete("Custom DocPerm", {"parent": "Address"})
		frappe.clear_cache(doctype="Address")
		for _run in range(2):
			grant_address_read_to_accounts_manager()
			rules = frappe.get_all(
				"Custom DocPerm",
				filters={"parent": "Address", "role": "Accounts Manager"},
				fields=["permlevel", "if_owner", "read", "export"],
			)
			self.assertEqual(len(rules), 1)
			self.assertEqual(
				(rules[0].permlevel, rules[0].if_owner, rules[0].read, rules[0].export), (0, 0, 1, 0)
			)
			self.assertEqual(self.address_rules_except_accounts_manager(), self.shipped_address_rules())
