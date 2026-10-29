import frappe
from frappe.core.page.permission_manager.permission_manager import remove
from frappe.permissions import setup_custom_perms

from erpnext.patches.v16_0 import (
	mirror_release_perms_to_custom_docperm,
	mirror_select_perms_to_custom_docperm,
	remove_all_role_from_payment_terms_template,
)
from erpnext.setup.install import grant_address_read_to_accounts_manager
from erpnext.tests.permission_test_utils import insert_test_record
from erpnext.tests.utils import ERPNextTestSuite


class TestPermissionPatches(ERPNextTestSuite):
	def tearDown(self):
		super().tearDown()
		for doctype in ("Payment Term", "Account", "Payment Terms Template", "Address"):
			frappe.clear_cache(doctype=doctype)

	def custom_rule(self, doctype, role):
		return frappe.db.get_value(
			"Custom DocPerm",
			{"parent": doctype, "role": role, "permlevel": 0},
			["select", "read"],
			as_dict=True,
		)

	def test_mirror_inserts_this_release_rules_on_a_customised_doctype(self):
		setup_custom_perms("Payment Term")
		frappe.db.delete("Custom DocPerm", {"parent": "Payment Term", "role": "Manufacturing Manager"})
		mirror_release_perms_to_custom_docperm.execute()
		self.assertEqual(self.custom_rule("Payment Term", "Manufacturing Manager").select, 1)
		setup_custom_perms("Account")
		frappe.db.delete("Custom DocPerm", {"parent": "Account", "role": "Quality Manager"})
		mirror_select_perms_to_custom_docperm.execute()
		self.assertEqual(self.custom_rule("Account", "Quality Manager").select, 1)

	def test_mirror_leaves_an_admin_removed_pair_alone(self):
		setup_custom_perms("Payment Term")
		remove("Payment Term", "Manufacturing Manager", 0)
		mirror_release_perms_to_custom_docperm.execute()
		self.assertIsNone(self.custom_rule("Payment Term", "Manufacturing Manager"))

	def test_all_row_is_removed_from_a_customised_payment_terms_template(self):
		setup_custom_perms("Payment Terms Template")
		insert_test_record(
			"Custom DocPerm",
			{
				"parent": "Payment Terms Template",
				"parenttype": "DocType",
				"parentfield": "permissions",
				"role": "All",
				"permlevel": 0,
				"select": 1,
				"read": 0,
				"export": 1,
			},
		)
		mirror_release_perms_to_custom_docperm.execute()
		remove_all_role_from_payment_terms_template.execute()
		self.assertFalse(
			frappe.db.exists(
				"Custom DocPerm", {"parent": "Payment Terms Template", "role": "All", "permlevel": 0}
			)
		)

	def test_address_grant_is_idempotent_and_keeps_other_roles(self):
		frappe.db.delete("Custom DocPerm", {"parent": "Address"})
		frappe.db.delete("Permission Log", {"for_document": "Address"})
		shipped = {}
		for rule in frappe.get_all(
			"DocPerm", filters={"parent": "Address", "permlevel": 0}, fields=["role", "read", "if_owner"]
		):
			shipped[(rule.role, rule.if_owner)] = rule.read
		grant_address_read_to_accounts_manager()
		grant_address_read_to_accounts_manager()
		accounts_manager = frappe.get_all(
			"Custom DocPerm",
			filters={"parent": "Address", "role": "Accounts Manager", "permlevel": 0},
			fields=["read"],
		)
		self.assertEqual(len(accounts_manager), 1)
		self.assertEqual(accounts_manager[0].read, 1)
		custom = {}
		for rule in frappe.get_all(
			"Custom DocPerm",
			filters={"parent": "Address", "permlevel": 0},
			fields=["role", "read", "if_owner"],
		):
			if rule.role != "Accounts Manager":
				custom[(rule.role, rule.if_owner)] = rule.read
		self.assertEqual(custom, shipped)
