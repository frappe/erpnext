
import frappe
import unittest

# Import the report file
from erpnext.accounts.report import non_billed_report
from erpnext.accounts.report.delivered_items_to_be_billed.delivered_items_to_be_billed import execute, get_column, get_args


class TestDeliveredItemsToBeBilled(unittest.TestCase):
    def test_get_columns_structure_TC_ACC_539(self):
        """Ensure columns contain expected keys and labels"""
        columns = get_column()

        # Check basic structure
        self.assertIsInstance(columns, list)
        self.assertGreater(len(columns), 5)

        # Ensure required fields exist
        col_fields = [col["fieldname"] for col in columns]
        self.assertIn("name", col_fields)
        self.assertIn("customer", col_fields)
        self.assertIn("item_code", col_fields)
        self.assertIn("pending_amount", col_fields)

    def test_get_args_structure_TC_ACC_540(self):
        """Ensure args dict has required keys"""
        args = get_args()
        required_keys = {"doctype", "party", "date", "order", "order_by", "reference_field"}
        self.assertTrue(required_keys.issubset(set(args.keys())))

        self.assertEqual(args["doctype"], "Delivery Note")
        self.assertEqual(args["party"], "customer")
        self.assertEqual(args["date"], "posting_date")

    def test_execute_without_filters_TC_ACC_541(self):
        """Run the report without filters to ensure it returns columns + data"""
        columns, data = execute(filters={})   # <-- changed from None

        self.assertIsInstance(columns, list)
        self.assertIsInstance(columns[0], dict)
        self.assertIsInstance(data, list)


    def test_execute_with_filters_TC_ACC_542(self):
        """Run the report with sample filters"""
        filters = {"customer": "_Test Customer"}
        columns, data = execute(filters)

        self.assertIsInstance(data, list)
        # Data may be empty in fresh sites, but type check is enough
        if data:
            self.assertIn("name", data[0])  # Delivery Note field


