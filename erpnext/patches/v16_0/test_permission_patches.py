# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.permissions import add_permission, update_permission_property

from erpnext.patches.v16_0 import (
	mirror_release_perms_to_custom_docperm,
	remove_all_role_from_payment_terms_template,
)
from erpnext.setup.install import grant_address_read_to_accounts_manager
from erpnext.tests.utils import ERPNextTestSuite

RIGHTS = (
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
TOUCHED_DOCTYPES = ("Payment Terms Template", "POS Invoice", "Serial and Batch Bundle", "Address")
ROLES_NEW_IN_RELEASE = {
	"Payment Terms Template": (
		"HR Manager",
		"Maintenance Manager",
		"Maintenance User",
		"Purchase Manager",
		"Purchase Master Manager",
		"Purchase User",
		"Sales Manager",
		"Sales Master Manager",
		"Sales User",
	),
	"Serial and Batch Bundle": ("Sales Manager", "Sales User"),
}
SELECT_ONLY_IN_PREVIOUS_RELEASE = {"POS Invoice": ("Sales Manager", "Sales User")}
PREVIOUS_ALL_ROW = ("select", "report", "export", "share", "print", "email")


class TestPermissionPatches(ERPNextTestSuite):
	def tearDown(self):
		super().tearDown()
		for doctype in TOUCHED_DOCTYPES:
			frappe.clear_cache(doctype=doctype)

	def insert_custom_docperm(self, doctype, role, rights, permlevel=0):
		row = frappe.new_doc("Custom DocPerm")
		row.update(
			{
				"parent": doctype,
				"parenttype": "DocType",
				"parentfield": "permissions",
				"role": role,
				"permlevel": permlevel,
				"if_owner": 0,
			}
		)
		for right in RIGHTS:
			row.set(right, 1 if right in rights else 0)
		row.insert(ignore_permissions=True)

	def customise_at_previous_release(self, doctype):
		frappe.db.delete("Custom DocPerm", {"parent": doctype})
		for perm in frappe.get_all("DocPerm", filters={"parent": doctype}, fields=["*"]):
			if perm.role in ROLES_NEW_IN_RELEASE.get(doctype, ()):
				continue
			rights = []
			for right in RIGHTS:
				if perm.get(right):
					rights.append(right)
			if perm.role in SELECT_ONLY_IN_PREVIOUS_RELEASE.get(doctype, ()) and not perm.permlevel:
				rights = ["select"]
			self.insert_custom_docperm(doctype, perm.role, rights, perm.permlevel)
		if doctype == "Payment Terms Template":
			self.insert_custom_docperm(doctype, "All", PREVIOUS_ALL_ROW)
		frappe.clear_cache(doctype=doctype)

	def get_rights(self, doctype, role):
		rows = []
		for perm in frappe.get_all(
			"Custom DocPerm",
			filters={"parent": doctype, "role": role, "permlevel": 0},
			fields=list(RIGHTS),
		):
			rights = []
			for right in RIGHTS:
				if perm.get(right):
					rights.append(right)
			rows.append(rights)
		return rows

	def get_rules(self, doctype, perm_doctype="Custom DocPerm"):
		rules = []
		for perm in frappe.get_all(
			perm_doctype,
			filters={"parent": doctype},
			fields=["role", "permlevel", "if_owner", *RIGHTS],
			order_by="role asc, permlevel asc, if_owner asc",
		):
			rule = [perm.role, perm.permlevel, perm.if_owner]
			for right in RIGHTS:
				rule.append(perm.get(right))
			rules.append(rule)
		return rules

	def test_mirror_carries_release_rules_into_previous_release_customisation(self):
		self.customise_at_previous_release("Payment Terms Template")
		self.customise_at_previous_release("POS Invoice")
		self.customise_at_previous_release("Serial and Batch Bundle")

		mirror_release_perms_to_custom_docperm.execute()

		self.assertEqual(self.get_rights("POS Invoice", "Sales User"), [["select", "read"]])
		self.assertEqual(self.get_rights("POS Invoice", "Sales Manager"), [["select", "read"]])
		self.assertEqual(self.get_rights("Serial and Batch Bundle", "Sales User"), [["select"]])
		self.assertEqual(self.get_rights("Serial and Batch Bundle", "Sales Manager"), [["select"]])
		for role in ("Maintenance Manager", "Maintenance User", "Purchase Manager", "Purchase User"):
			self.assertEqual(self.get_rights("Payment Terms Template", role), [["read"]])
		for role in ("Sales Manager", "Sales User"):
			self.assertEqual(self.get_rights("Payment Terms Template", role), [["read"]])
		for role in ("HR Manager", "Purchase Master Manager", "Sales Master Manager"):
			self.assertEqual(self.get_rights("Payment Terms Template", role), [["select"]])

		before = self.get_rules("Payment Terms Template")
		mirror_release_perms_to_custom_docperm.execute()
		self.assertEqual(self.get_rules("Payment Terms Template"), before)

	def test_mirror_leaves_admin_changed_pairs_alone(self):
		self.customise_at_previous_release("Payment Terms Template")
		self.customise_at_previous_release("POS Invoice")

		update_permission_property("POS Invoice", "Sales User", 0, "print", 1)
		add_permission("Payment Terms Template", "Purchase User", 0, "read")
		frappe.delete_doc(
			"Custom DocPerm",
			frappe.db.get_value(
				"Custom DocPerm", {"parent": "Payment Terms Template", "role": "Purchase User"}
			),
			ignore_permissions=True,
		)
		add_permission("Payment Terms Template", "Sales User", 0, "select")
		update_permission_property("Payment Terms Template", "Sales User", 0, "read", 0)
		update_permission_property("Payment Terms Template", "Sales User", 0, "export", 0)

		mirror_release_perms_to_custom_docperm.execute()

		self.assertEqual(self.get_rights("POS Invoice", "Sales User"), [["select", "print"]])
		self.assertEqual(self.get_rights("POS Invoice", "Sales Manager"), [["select", "read"]])
		self.assertEqual(self.get_rights("Payment Terms Template", "Purchase User"), [])
		self.assertEqual(self.get_rights("Payment Terms Template", "Sales User"), [["select"]])
		self.assertEqual(self.get_rights("Payment Terms Template", "Sales Manager"), [["read"]])

	def test_mirror_skips_doctypes_without_custom_rules(self):
		frappe.db.delete("Custom DocPerm", {"parent": "Payment Terms Template"})
		frappe.clear_cache(doctype="Payment Terms Template")

		mirror_release_perms_to_custom_docperm.execute()

		self.assertEqual(self.get_rules("Payment Terms Template"), [])

	def test_remove_all_role_from_customised_payment_terms_template(self):
		frappe.db.delete("Custom DocPerm", {"parent": "Payment Terms Template"})
		remove_all_role_from_payment_terms_template.execute()
		self.assertEqual(self.get_rules("Payment Terms Template"), [])

		self.customise_at_previous_release("Payment Terms Template")
		self.assertEqual(self.get_rights("Payment Terms Template", "All"), [list(PREVIOUS_ALL_ROW)])
		others = []
		for rule in self.get_rules("Payment Terms Template"):
			if rule[0] != "All":
				others.append(rule)

		remove_all_role_from_payment_terms_template.execute()

		self.assertEqual(self.get_rights("Payment Terms Template", "All"), [])
		self.assertEqual(self.get_rules("Payment Terms Template"), others)

	def test_grant_address_read_is_idempotent_and_keeps_other_roles(self):
		frappe.db.delete("Custom DocPerm", {"parent": "Address"})
		frappe.clear_cache(doctype="Address")
		standard = self.get_rules("Address", "DocPerm")

		grant_address_read_to_accounts_manager()
		first = self.get_rules("Address")
		grant_address_read_to_accounts_manager()

		self.assertEqual(self.get_rules("Address"), first)
		self.assertEqual(self.get_rights("Address", "Accounts Manager"), [["read"]])
		others = []
		for rule in first:
			if rule[0] != "Accounts Manager":
				others.append(rule)
		self.assertEqual(others, standard)

	def test_grant_address_read_leaves_an_admin_removed_rule_alone(self):
		frappe.db.delete("Custom DocPerm", {"parent": "Address"})
		frappe.clear_cache(doctype="Address")
		add_permission("Address", "Accounts Manager", 0, "read")
		frappe.delete_doc(
			"Custom DocPerm",
			frappe.db.get_value("Custom DocPerm", {"parent": "Address", "role": "Accounts Manager"}),
			ignore_permissions=True,
		)
		before = self.get_rules("Address")

		grant_address_read_to_accounts_manager()

		self.assertEqual(self.get_rights("Address", "Accounts Manager"), [])
		self.assertEqual(self.get_rules("Address"), before)
