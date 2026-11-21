import frappe
from frappe.core.page.permission_manager.permission_manager import remove
from frappe.permissions import setup_custom_perms

from erpnext.patches.v16_0 import (
	mirror_release_perms_to_custom_docperm,
	mirror_select_perms_to_custom_docperm,
	remove_all_role_from_payment_terms_template,
	restrict_employee_project_perms_to_select,
)
from erpnext.setup.install import setup_company_address_permissions
from erpnext.tests.permission_test_utils import insert_test_record
from erpnext.tests.utils import ERPNextTestSuite


class TestPermissionPatches(ERPNextTestSuite):
	def tearDown(self):
		super().tearDown()
		for doctype in ("Payment Term", "Account", "Payment Terms Template", "Address", "Project"):
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

	def set_employee_project_rule(self, **rights):
		"""Give the site a customised Employee rule on Project that still has the old shipped rights."""
		setup_custom_perms("Project")
		name = frappe.db.get_value(
			"Custom DocPerm", {"parent": "Project", "role": "Employee", "permlevel": 0}
		)
		frappe.db.set_value(
			"Custom DocPerm",
			name,
			{"select": 1, "print": 1, "email": 1, "export": 1, "report": 1, "share": 1, **rights},
		)
		return name

	def employee_project_rights(self, name):
		return frappe.db.get_value(
			"Custom DocPerm",
			name,
			["select", "read", "print", "email", "export", "report", "share"],
			as_dict=True,
		)

	def test_employee_project_rule_keeps_only_select(self):
		name = self.set_employee_project_rule()
		restrict_employee_project_perms_to_select.execute()
		rights = self.employee_project_rights(name)
		self.assertEqual(rights.select, 1)
		for ptype in restrict_employee_project_perms_to_select.PTYPES:
			self.assertEqual(rights[ptype], 0, ptype)

	def test_employee_project_rule_with_read_is_kept(self):
		name = self.set_employee_project_rule(read=1)
		before = self.employee_project_rights(name)
		restrict_employee_project_perms_to_select.execute()
		self.assertEqual(self.employee_project_rights(name), before)

	def test_employee_project_rule_at_higher_level_is_kept(self):
		self.set_employee_project_rule()
		name = insert_test_record(
			"Custom DocPerm",
			{
				"parent": "Project",
				"parenttype": "DocType",
				"parentfield": "permissions",
				"role": "Employee",
				"permlevel": 1,
				"print": 1,
				"email": 1,
				"export": 1,
				"report": 1,
				"share": 1,
			},
		)
		before = self.employee_project_rights(name)
		restrict_employee_project_perms_to_select.execute()
		self.assertEqual(self.employee_project_rights(name), before)

	def test_address_grant_is_idempotent_and_keeps_other_roles(self):
		frappe.db.delete("Custom DocPerm", {"parent": "Address"})
		frappe.db.delete("Permission Log", {"for_document": "Address"})
		shipped = {}
		for rule in frappe.get_all(
			"DocPerm", filters={"parent": "Address", "permlevel": 0}, fields=["role", "read", "if_owner"]
		):
			shipped[(rule.role, rule.if_owner)] = rule.read
		setup_company_address_permissions()
		setup_company_address_permissions()
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
