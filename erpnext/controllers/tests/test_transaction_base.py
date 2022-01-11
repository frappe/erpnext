import unittest

import frappe


class TestUtils(unittest.TestCase):
    def test_reset_default_field_value(self):
        doc = frappe.get_doc({
            "doctype": "Purchase Receipt",
            "set_warehouse": "Warehouse 1",
        })

        # Same values
        doc.items = [{"warehouse": "Warehouse 1"}, {"warehouse": "Warehouse 1"}, {"warehouse": "Warehouse 1"}]
        doc.reset_default_field_value("set_warehouse", "items", "warehouse")
        self.assertEqual(doc.set_warehouse, "Warehouse 1")

        # Mixed values
        doc.items = [{"warehouse": "Warehouse 1"}, {"warehouse": "Warehouse 2"}, {"warehouse": "Warehouse 1"}]
        doc.reset_default_field_value("set_warehouse", "items", "warehouse")
        self.assertEqual(doc.set_warehouse, None)

