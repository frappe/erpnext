"""Tests for ``erpnext.cerbos_authz.principal.build_principal``."""

import importlib
import unittest

from tests.cerbos_authz._stubs import install_stubs


class BuildPrincipalTests(unittest.TestCase):
    def setUp(self):
        self.frappe = install_stubs()
        self.principal_module = importlib.import_module(
            "erpnext.cerbos_authz.principal"
        )

    def test_internal_user_with_company_user_permission(self):
        self.frappe.user_roles["alice@acme.test"] = ["Accounts User"]
        self.frappe.get_all_results["User Permission"] = [
            {"user": "alice@acme.test", "allow": "Company", "for_value": "Acme"},
        ]
        self.frappe.user_defaults[("alice@acme.test", "company")] = "Acme"

        p = self.principal_module.build_principal("alice@acme.test")

        self.assertEqual(p.id, "alice@acme.test")
        self.assertEqual(p.roles, ["Accounts User"])
        self.assertEqual(p.attr["user_type"], "System User")
        self.assertEqual(p.attr["company"], "Acme")
        self.assertEqual(p.attr["allowed_companies"], ["Acme"])
        self.assertNotIn("customer", p.attr)
        self.assertNotIn("supplier", p.attr)

    def test_user_with_no_company_user_permissions_sees_all_companies(self):
        # Frappe convention: no User Permission rows = unrestricted.
        self.frappe.user_roles["sysmgr@acme.test"] = ["System Manager"]
        self.frappe.get_all_results["User Permission"] = []
        self.frappe.get_all_results["Company"] = [{"name": "Acme"}, {"name": "Globex"}]

        p = self.principal_module.build_principal("sysmgr@acme.test")

        self.assertEqual(set(p.attr["allowed_companies"]), {"Acme", "Globex"})

    def test_portal_customer_user(self):
        self.frappe.user_roles["alice@bigco.test"] = ["Customer"]
        self.frappe.get_all_results["Portal User"] = [
            {"user": "alice@bigco.test", "parenttype": "Customer", "parent": "BigCo"},
        ]

        p = self.principal_module.build_principal("alice@bigco.test")

        self.assertEqual(p.attr["user_type"], "Website User")
        self.assertEqual(p.attr["customer"], "BigCo")
        self.assertNotIn("supplier", p.attr)

    def test_portal_supplier_user(self):
        self.frappe.user_roles["bob@megasupply.test"] = ["Supplier"]
        self.frappe.get_all_results["Portal User"] = [
            {"user": "bob@megasupply.test", "parenttype": "Supplier", "parent": "MegaSupply"},
        ]

        p = self.principal_module.build_principal("bob@megasupply.test")

        self.assertEqual(p.attr["user_type"], "Website User")
        self.assertEqual(p.attr["supplier"], "MegaSupply")

    def test_employee_link_and_approver_lists(self):
        self.frappe.user_roles["carol@acme.test"] = ["Employee", "HR User"]
        self.frappe.db_values[("Employee", (("user_id", "carol@acme.test"),), "name")] = "EMP-0003"
        self.frappe.db_values[("Employee", (("user_id", "carol@acme.test"),), "department")] = "HR"
        self.frappe.get_all_results["Employee"] = [
            {"name": "EMP-0001", "leave_approver": "carol@acme.test", "expense_approver": "carol@acme.test", "status": "Active"},
            {"name": "EMP-0002", "leave_approver": "someone.else@acme.test", "status": "Active"},
        ]

        p = self.principal_module.build_principal("carol@acme.test")

        self.assertEqual(p.attr["employee"], "EMP-0003")
        self.assertEqual(p.attr["department"], "HR")
        self.assertEqual(p.attr["leave_approver_for"], ["EMP-0001"])
        self.assertEqual(p.attr["expense_approver_for"], ["EMP-0001"])

    def test_administrator_does_not_get_party_links(self):
        self.frappe.user_roles["Administrator"] = ["System Manager"]
        # Even if Portal User rows exist, Administrator/Guest must not be linked.
        self.frappe.get_all_results["Portal User"] = [
            {"user": "Administrator", "parenttype": "Customer", "parent": "BigCo"},
        ]
        p = self.principal_module.build_principal("Administrator")
        self.assertNotIn("customer", p.attr)


if __name__ == "__main__":
    unittest.main()
