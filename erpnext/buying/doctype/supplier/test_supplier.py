# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals


import frappe, unittest
from erpnext.accounts.party import get_due_date
from erpnext.exceptions import PartyDisabled
from frappe.test_runner import make_test_records
from erpnext import get_default_company

test_dependencies = ['Payment Term', 'Payment Terms Template']
test_records = frappe.get_test_records('Supplier')


class TestSupplier(unittest.TestCase):
    def test_supplier_default_payment_terms(self):
        # Payment Term based on Days after invoice date
        frappe.db.set_value(
            "Supplier", "_Test Supplier With Template 1", "payment_terms", "_Test Payment Term Template 3")

        due_date = get_due_date("2016-01-22", "Supplier", "_Test Supplier With Template 1")
        self.assertEqual(due_date, "2016-02-21")

        due_date = get_due_date("2017-01-22", "Supplier", "_Test Supplier With Template 1")
        self.assertEqual(due_date, "2017-02-21")

        # Payment Term based on last day of month
        frappe.db.set_value(
            "Supplier", "_Test Supplier With Template 1", "payment_terms", "_Test Payment Term Template 1")

        due_date = get_due_date("2016-01-22", "Supplier", "_Test Supplier With Template 1")
        self.assertEqual(due_date, "2016-02-29")

        due_date = get_due_date("2017-01-22", "Supplier", "_Test Supplier With Template 1")
        self.assertEqual(due_date, "2017-02-28")

        frappe.db.set_value("Supplier", "_Test Supplier With Template 1", "payment_terms", "")

        # Set credit limit for the supplier group instead of supplier and evaluate the due date
        frappe.db.set_value("Supplier Group", "_Test Supplier Group", "payment_terms", "_Test Payment Term Template 3")

        due_date = get_due_date("2016-01-22", "Supplier", "_Test Supplier With Template 1")
        self.assertEqual(due_date, "2016-02-21")

        # Payment terms for Supplier Group instead of supplier and evaluate the due date
        frappe.db.set_value("Supplier Group", "_Test Supplier Group", "payment_terms", "_Test Payment Term Template 1")

        # Leap year
        due_date = get_due_date("2016-01-22", "Supplier", "_Test Supplier With Template 1")
        self.assertEqual(due_date, "2016-02-29")
        # # Non Leap year
        due_date = get_due_date("2017-01-22", "Supplier", "_Test Supplier With Template 1")
        self.assertEqual(due_date, "2017-02-28")

        # Supplier with no default Payment Terms Template
        frappe.db.set_value("Supplier Group", "_Test Supplier Group", "payment_terms", "")
        frappe.db.set_value("Supplier", "_Test Supplier", "payment_terms", "")

        due_date = get_due_date("2016-01-22", "Supplier", "_Test Supplier")
        self.assertEqual(due_date, "2016-01-22")
        # # Non Leap year
        due_date = get_due_date("2017-01-22", "Supplier", "_Test Supplier")
        self.assertEqual(due_date, "2017-01-22")

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

        def get_suplier_dict(supplier_name):
        	return {
        		 "supplier_group": "_Test Supplier Group",
        		 "supplier_name": supplier_name,
        		 "doctype": "Suplier",
        		 "tax_id": 00000
        	}

        def test_supplier_account(self):
        	company_abbr = frappe.db.get_value("Company", get_default_company(), "abbr")
        	test_account = '_Test Supplier 1 - {}'.format(company_abbr)
        	if frappe.db.get_single_value('Accounts Settings', 'create_supplier_account_after_insert'):
        		frappe.db.sql("delete from `tabSupplier` where supplier_name='_Test Supplier 1'")
        		frappe.db.sql("delete from `tabAccount` where name=%s",test_account)
        		frappe.get_doc(get_supplier_dict('_Test Supplier 1')).insert(ignore_permissions=True)
        		self.assertTrue(frappe.db.exists("Account", "_Test Supplier 1 - {}".format(company_abbr)))
