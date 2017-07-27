# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals


import frappe, unittest
from erpnext.accounts.party import get_due_date
from erpnext.exceptions import PartyFrozen, PartyDisabled
from frappe.test_runner import make_test_records

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


    def test_supplier_disabled(self):
        make_test_records("Item")

        frappe.db.set_value("Supplier", "_Test Supplier", "disabled", 1)

        from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order

        po = create_purchase_order(do_not_save=True)

        self.assertRaises(PartyDisabled, po.save)

        frappe.db.set_value("Supplier", "_Test Supplier", "disabled", 0)

        po.save()


    def test_supplier_country(self):
        # Test that country field exists in Supplier DocType
        supplier = frappe.get_doc('Supplier', '_Test Supplier with Country')
        self.assertTrue('country' in supplier.as_dict())

        # Test if test supplier field record is 'Greece'
        self.assertEqual(supplier.country, "Greece")

        # Test update Supplier instance country value
        supplier = frappe.get_doc('Supplier', '_Test Supplier')
        supplier.country = 'Greece'
        supplier.save()
        self.assertEqual(supplier.country, "Greece")
