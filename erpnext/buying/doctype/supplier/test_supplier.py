# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.accounts.party import get_due_date

test_records = frappe.get_test_records('Supplier')

class TestSupplier(unittest.TestCase):
    def test_supplier_due_date_against_supplier_credit_limit(self):
        # Set Credit Limit based on Fixed days
        frappe.db.set_value("Supplier", "_Test Supplier", "credit_days_based_on", "Fixed Days")
        frappe.db.set_value("Supplier", "_Test Supplier", "credit_days", 10)

        due_date = get_due_date("2016-01-22", "Supplier", "_Test Supplier", "_Test Company")
        self.assertEqual(due_date, "2016-02-01")

        # Set Credit Limit based on Last day next month
        frappe.db.set_value("Supplier", "_Test Supplier", "credit_days", 0)
        frappe.db.set_value("Supplier", "_Test Supplier", "credit_days_based_on",
                            "Last Day of the Next Month")

        # Leap year
        due_date = get_due_date("2016-01-22", "Supplier", "_Test Supplier", "_Test Company")
        self.assertEqual(due_date, "2016-02-29")
        # Non Leap year
        due_date = get_due_date("2017-01-22", "Supplier", "_Test Supplier", "_Test Company")
        self.assertEqual(due_date, "2017-02-28")

        frappe.db.set_value("Supplier", "_Test Supplier", "credit_days_based_on", "")

        # Set credit limit for the supplier type instead of supplier and evaluate the due date
        # based on Fixed days
        frappe.db.set_value("Supplier Type", "_Test Supplier Type", "credit_days_based_on",
                            "Fixed Days")
        frappe.db.set_value("Supplier Type", "_Test Supplier Type", "credit_days", 10)

        due_date = get_due_date("2016-01-22", "Supplier", "_Test Supplier", "_Test Company")
        self.assertEqual(due_date, "2016-02-01")

        # Set credit limit for the supplier type instead of supplier and evaluate the due date
        # based on Last day of next month
        frappe.db.set_value("Supplier", "_Test Supplier Type", "credit_days", 0)
        frappe.db.set_value("Supplier Type", "_Test Supplier Type", "credit_days_based_on",
                            "Last Day of the Next Month")

        # Leap year
        due_date = get_due_date("2016-01-22", "Supplier", "_Test Supplier", "_Test Company")
        self.assertEqual(due_date, "2016-02-29")
        # Non Leap year
        due_date = get_due_date("2017-01-22", "Supplier", "_Test Supplier", "_Test Company")
        self.assertEqual(due_date, "2017-02-28")
