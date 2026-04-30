"""Tests for ``erpnext.cerbos_authz.resources.build_resource``."""

import importlib
import unittest

from tests.cerbos_authz._stubs import install_stubs


def _doc(d):
    """Wrap a plain dict as a duck-typed Frappe Document."""
    class _D:
        def __init__(self, data):
            self._data = data

        def get(self, key, default=None):
            return self._data.get(key, default)

    return _D(d)


class BuildResourceTests(unittest.TestCase):
    def setUp(self):
        self.frappe = install_stubs()
        self.resources_module = importlib.import_module(
            "erpnext.cerbos_authz.resources"
        )

    def _build(self, doctype, doc_dict):
        return self.resources_module.build_resource(doctype, _doc(doc_dict))

    def test_unknown_doctype_returns_none(self):
        self.assertIsNone(self._build("ToDo", {"name": "T-1"}))

    def test_sales_invoice_includes_country_from_company(self):
        self.frappe.db_values[("Company", "Acme", "country")] = "India"
        r = self._build(
            "Sales Invoice",
            {
                "name": "SINV-001",
                "company": "Acme",
                "owner": "alice@acme.test",
                "docstatus": 1,
                "customer": "BigCo",
                "is_return": False,
            },
        )
        self.assertEqual(r.kind, "sales_invoice")
        self.assertEqual(r.id, "SINV-001")
        self.assertEqual(r.attr["company"], "Acme")
        self.assertEqual(r.attr["customer"], "BigCo")
        self.assertEqual(r.attr["docstatus"], 1)
        self.assertEqual(r.attr["country"], "India")
        self.assertEqual(r.attr["is_return"], False)

    def test_purchase_invoice_uses_supplier(self):
        self.frappe.db_values[("Company", "Acme", "country")] = "Nepal"
        r = self._build(
            "Purchase Invoice",
            {
                "name": "PINV-001",
                "company": "Acme",
                "owner": "alice@acme.test",
                "docstatus": 0,
                "supplier": "MegaSupply",
            },
        )
        self.assertEqual(r.kind, "purchase_invoice")
        self.assertEqual(r.attr["supplier"], "MegaSupply")
        self.assertEqual(r.attr["country"], "Nepal")

    def test_quotation_falls_back_to_party_name(self):
        # Quotation stores the customer in `party_name`, not `customer`.
        r = self._build(
            "Quotation",
            {
                "name": "QTN-001",
                "company": "Acme",
                "owner": "sales@acme.test",
                "docstatus": 0,
                "party_name": "BigCo",
                "status": "Draft",
            },
        )
        self.assertEqual(r.attr["customer"], "BigCo")

    def test_employee_carries_user_id(self):
        r = self._build(
            "Employee",
            {
                "name": "EMP-0001",
                "company": "Acme",
                "owner": "hr@acme.test",
                "user_id": "alice@acme.test",
                "department": "Engineering",
                "status": "Active",
            },
        )
        self.assertEqual(r.attr["user_id"], "alice@acme.test")
        self.assertEqual(r.attr["status"], "Active")

    def test_task_parses_assigned_to_json(self):
        r = self._build(
            "Task",
            {
                "name": "TASK-1",
                "owner": "pm@acme.test",
                "_assign": '["alice@acme.test", "bob@acme.test"]',
                "status": "Open",
                "project": "PROJ-1",
            },
        )
        self.assertEqual(
            r.attr["assigned_to"], ["alice@acme.test", "bob@acme.test"]
        )

    def test_task_handles_missing_assign(self):
        r = self._build(
            "Task",
            {"name": "TASK-2", "owner": "x@y.test", "status": "Open", "project": "P"},
        )
        self.assertEqual(r.attr["assigned_to"], [])

    def test_task_handles_garbage_assign_field(self):
        r = self._build(
            "Task",
            {"name": "TASK-3", "owner": "x@y.test", "_assign": "not-json"},
        )
        self.assertEqual(r.attr["assigned_to"], [])

    def test_docstatus_default_is_zero(self):
        r = self._build(
            "Stock Entry",
            {"name": "STE-1", "company": "Acme", "owner": "stock@acme.test"},
        )
        self.assertEqual(r.attr["docstatus"], 0)


if __name__ == "__main__":
    unittest.main()
