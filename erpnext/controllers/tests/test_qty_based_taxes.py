from __future__ import unicode_literals, print_function
import unittest
import frappe
from uuid import uuid4 as _uuid4

def uuid4():
    return str(_uuid4())

class TestTaxes(unittest.TestCase):
    def setUp(self):
        self.company = frappe.get_doc({
            'doctype': 'Company',
            'company_name': uuid4(),
            'abbr': ''.join(s[0] for s in uuid4().split('-')),
            'default_currency': 'USD',
        }).insert()
        self.account = frappe.get_doc({
            'doctype': 'Account',
            'account_name': uuid4(),
            'account_type': 'Tax',
            'company': self.company.name,
            'parent_account': 'Duties and Taxes - {self.company.abbr}'.format(self=self)
        }).insert()
        self.item_group = frappe.get_doc({
            'doctype': 'Item Group',
            'item_group_name': uuid4(),
            'parent_item_group': 'All Item Groups',
        }).insert()
        self.item = frappe.get_doc({
            'doctype': 'Item',
            'item_code': uuid4(),
            'item_group': self.item_group.name,
            'is_stock_item': 0,
            'taxes': [
                {
                    'tax_type': self.account.name,
                    'tax_rate': 2,
                }
            ],
        }).insert()
        self.customer = frappe.get_doc({
            'doctype': 'Customer',
            'customer_name': uuid4(),
            'customer_group': 'All Customer Groups',
        }).insert()
        self.supplier = frappe.get_doc({
            'doctype': 'Supplier',
            'supplier_name': uuid4(),
            'supplier_group': 'All Supplier Groups',
        }).insert()

    def test_taxes(self):
        self.created_docs = []
        for dt in ['Purchase Order', 'Purchase Receipt', 'Purchase Invoice',
                'Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice']:
            doc = frappe.get_doc({
                'doctype': dt,
                'company': self.company.name,
                'supplier': self.supplier.name,
                'schedule_date': frappe.utils.nowdate(),
                'delivery_date': frappe.utils.nowdate(),
                'customer': self.customer.name,
                'buying_price_list' if dt.startswith('Purchase') else 'selling_price_list'
                : 'Standard Buying' if dt.startswith('Purchase') else 'Standard Selling',
                'items': [
                    {
                        'item_code': self.item.name,
                        'qty': 300,
                        'rate': 100,
                    }
                ],
                'taxes': [
                    {
                        'charge_type': 'On Item Quantity',
                        'account_head': self.account.name,
                        'description': 'N/A',
                        'rate': 0,
                    },
                ],
            })
            doc.run_method('set_missing_values')
            doc.run_method('calculate_taxes_and_totals')
            doc.insert()
            self.assertEqual(doc.taxes[0].tax_amount, 600)
            self.created_docs.append(doc)

    def tearDown(self):
        for doc in self.created_docs:
            doc.delete()
        self.item.delete()
        self.item_group.delete()
        self.account.delete()
        self.company.delete()
