"""Tests for ``erpnext.cerbos_authz.hooks``.

Covers:
- Administrator bypass.
- Unknown doctype passthrough (``None`` so Frappe falls back to its default).
- ALLOW / DENY round trip via the stubbed PDP client.
- Fail-closed behaviour when the PDP raises.
- Permission-query SQL generation for portal users.
"""

import importlib
import unittest

from tests.cerbos_authz._stubs import install_stubs


def _doc(doctype, data):
    class _D:
        def __init__(self):
            self.doctype = doctype
            self._data = dict(data)

        def get(self, key, default=None):
            if key == "doctype":
                return self.doctype
            return self._data.get(key, default)

    return _D()


class HasPermissionTests(unittest.TestCase):
    def setUp(self):
        self.frappe = install_stubs()
        self.client_module = importlib.import_module("erpnext.cerbos_authz.client")
        self.client_module.reset_client_for_testing()
        self.hooks_module = importlib.import_module("erpnext.cerbos_authz.hooks")

    def _last_client(self):
        return self.client_module.get_client()

    def _seed_principal(self, user, roles, company="Acme"):
        self.frappe.user_roles[user] = list(roles)
        self.frappe.user_defaults[(user, "company")] = company
        self.frappe.get_all_results.setdefault("User Permission", []).append(
            {"user": user, "allow": "Company", "for_value": company}
        )

    def test_administrator_bypass(self):
        doc = _doc("Sales Invoice", {"name": "SINV-1", "company": "Acme", "docstatus": 0})
        self.assertTrue(
            self.hooks_module.cerbos_has_permission(doc, "read", "Administrator")
        )

    def test_unknown_doctype_returns_none(self):
        # Returning None lets Frappe fall back to the framework default.
        self._seed_principal("alice@acme.test", ["Accounts User"])
        doc = _doc("ToDo", {"name": "T-1"})
        self.assertIsNone(
            self.hooks_module.cerbos_has_permission(doc, "read", "alice@acme.test")
        )

    def test_known_doctype_round_trips_through_pdp(self):
        self._seed_principal("alice@acme.test", ["Accounts User"])
        doc = _doc(
            "Sales Invoice",
            {"name": "SINV-1", "company": "Acme", "owner": "alice@acme.test", "docstatus": 0, "customer": "BigCo"},
        )
        result = self.hooks_module.cerbos_has_permission(doc, "read", "alice@acme.test")
        self.assertTrue(result)

        client = self._last_client()
        self.assertEqual(len(client.calls), 1)
        action, principal, resource = client.calls[0]
        self.assertEqual(action, "read")
        self.assertEqual(principal.id, "alice@acme.test")
        self.assertEqual(resource.kind, "sales_invoice")
        self.assertEqual(resource.attr["customer"], "BigCo")

    def test_pdp_deny_returns_false(self):
        self._seed_principal("alice@acme.test", ["Accounts User"])
        client = self._last_client()
        client.next_decision = False

        doc = _doc(
            "Sales Invoice",
            {"name": "SINV-1", "company": "Acme", "owner": "x@y.test", "docstatus": 1, "customer": "BigCo"},
        )
        self.assertFalse(
            self.hooks_module.cerbos_has_permission(doc, "write", "alice@acme.test")
        )

    def test_pdp_error_fails_closed_by_default(self):
        self._seed_principal("alice@acme.test", ["Accounts User"])
        client = self._last_client()
        client.raise_on_call = RuntimeError("PDP unreachable")

        doc = _doc(
            "Sales Invoice",
            {"name": "SINV-1", "company": "Acme", "owner": "x@y.test", "docstatus": 0, "customer": "BigCo"},
        )
        self.assertFalse(
            self.hooks_module.cerbos_has_permission(doc, "read", "alice@acme.test")
        )
        self.assertEqual(len(self.frappe.logged_errors), 1)

    def test_pdp_error_can_fail_open_when_configured(self):
        self.frappe.conf["cerbos_fail_closed"] = False
        self._seed_principal("alice@acme.test", ["Accounts User"])
        client = self._last_client()
        client.raise_on_call = RuntimeError("PDP unreachable")

        doc = _doc(
            "Sales Invoice",
            {"name": "SINV-1", "company": "Acme", "owner": "x@y.test", "docstatus": 0, "customer": "BigCo"},
        )
        # None defers to framework default rather than denying.
        self.assertIsNone(
            self.hooks_module.cerbos_has_permission(doc, "read", "alice@acme.test")
        )

    def test_query_conditions_empty_for_admin_and_guest(self):
        self.assertEqual(
            self.hooks_module.cerbos_permission_query_conditions("Administrator"), ""
        )
        self.assertEqual(
            self.hooks_module.cerbos_permission_query_conditions("Guest"), ""
        )

    def test_query_conditions_for_customer_portal_user(self):
        self.frappe.user_roles["alice@bigco.test"] = ["Customer"]
        self.frappe.get_all_results["Portal User"] = [
            {"user": "alice@bigco.test", "parenttype": "Customer", "parent": "BigCo"},
            {"user": "alice@bigco.test", "parenttype": "Customer", "parent": "BigCo Subsidiary"},
        ]
        sql = self.hooks_module.cerbos_permission_query_conditions("alice@bigco.test")
        self.assertIn(
            "`tab{doctype}`.`customer` in ('BigCo', 'BigCo Subsidiary')", sql
        )
        self.assertNotIn("supplier", sql)

    def test_query_conditions_for_supplier_portal_user(self):
        self.frappe.user_roles["bob@megasupply.test"] = ["Supplier"]
        self.frappe.get_all_results["Portal User"] = [
            {"user": "bob@megasupply.test", "parenttype": "Supplier", "parent": "MegaSupply"},
        ]
        sql = self.hooks_module.cerbos_permission_query_conditions("bob@megasupply.test")
        self.assertIn("`tab{doctype}`.`supplier` in ('MegaSupply')", sql)

    def test_query_conditions_internal_user_is_empty(self):
        self.frappe.user_roles["acct@acme.test"] = ["Accounts User"]
        # No Portal User rows.
        self.assertEqual(
            self.hooks_module.cerbos_permission_query_conditions("acct@acme.test"), ""
        )


class ThunkTests(unittest.TestCase):
    """The per-doctype thunks injected into ``hooks.HAS_PERMISSION_HOOKS``."""

    def setUp(self):
        self.frappe = install_stubs()
        self.client_module = importlib.import_module("erpnext.cerbos_authz.client")
        self.client_module.reset_client_for_testing()
        self.hooks_module = importlib.import_module("erpnext.cerbos_authz.hooks")

    def test_thunk_injects_doctype_for_dict_callers(self):
        # Some callers pass a plain dict without a ``doctype`` key.
        self.frappe.user_roles["alice@acme.test"] = ["Accounts User"]
        self.frappe.user_defaults[("alice@acme.test", "company")] = "Acme"
        self.frappe.get_all_results["User Permission"] = [
            {"user": "alice@acme.test", "allow": "Company", "for_value": "Acme"},
        ]

        thunk = self.hooks_module.HAS_PERMISSION_HOOKS["Sales Invoice"]
        result = thunk(
            {"name": "SINV-1", "company": "Acme", "owner": "x@y.test", "docstatus": 0, "customer": "BigCo"},
            ptype="read",
            user="alice@acme.test",
        )
        self.assertTrue(result)
        client = self.client_module.get_client()
        self.assertEqual(client.calls[-1][2].kind, "sales_invoice")


if __name__ == "__main__":
    unittest.main()
