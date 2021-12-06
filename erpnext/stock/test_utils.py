import unittest

import frappe

from erpnext.stock.utils import reset_default_field


class TestUtils(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_reset_default_field(self):
        doc = frappe.get_doc({
            "doctype": "Purchase Receipt",
            "set_warehouse": "Warehouse 1",
            "items": [],
        })

        # Same values
        doc.items = [{"warehouse": "Warehouse 1"}, {"warehouse": "Warehouse 1"}, {"warehouse": "Warehouse 1"}]

        reset_default_field(doc, "set_warehouse", "items", "warehouse")

        self.assertEqual(doc.set_warehouse, "Warehouse 1")

        # Mixed values
        doc.items = [{"warehouse": "Warehouse 1"}, {"warehouse": "Warehouse 2"}, {"warehouse": "Warehouse 1"}]

        reset_default_field(doc, "set_warehouse", "items", "warehouse")

        self.assertEqual(doc.set_warehouse, None)

