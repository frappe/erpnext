import frappe
import frappe.defaults
from frappe.tests.utils import FrappeTestCase

import unittest


class TestVAT(unittest.TestCase):
    """Test VAT functionality.
    
    This test creates a new company and tests that VAT is applied correctly to sales and purchase invoices.
    
    This test focuses on checking that different VAT accounts can be affected for sales and purchase invoices.
    """

    def setUp(self):
        unique_id = frappe.generate_hash("", 10)
        # Login as Administrator
        frappe.set_user("Administrator")

        # Create a new company
        company_name = "_Test Company CH" + unique_id
        # self.company = frappe.db.exists("Company", company_name)
        # if not self.company:
        self.company = frappe.get_doc(
            {
                "doctype": "Company",
                "company_name": company_name,
                "country": "Switzerland",
                "abbr": "test_company_ch" + unique_id,
                "default_currency": "CHF",
            }
        ).insert()
        # else:
        #     self.company = frappe.get_doc("Company", self.company)

        # Get default cost center for company
        self.cost_center = frappe.db.get_value("Company", self.company.name, "cost_center")


        # Get accounts from created company
        accounts = frappe.get_all("Account", fields=["name", "account_name", "account_type", "root_type", "parent_account"], 
                                  filters={"company": self.company.name, "is_group": 1, "account_type": "Tax"})
        
        # assert that at least one account is found
        self.assertTrue(len(accounts) > 0)
        
    
        # Create an account for VAT when selling
        self.vat_sales_account = frappe.get_doc({
            "doctype": "Account",
            "company": self.company.name,
            "account_name": "VAT - Sales",
            "account_type": "Tax",
            "root_type": "Asset",
            "parent_account": accounts[0].name,
        }).insert()

        # Create an account for VAT when buying
        self.vat_purchase_account = frappe.get_doc({
            "doctype": "Account",
            "company": self.company.name,
            "account_name": "VAT - Purchase",
            "account_type": "Tax",
            "root_type": "Asset",
            "parent_account": accounts[0].name,
        }).insert()

        # Create Item tax template
        self.item_tax_template = frappe.get_doc({
            "doctype": "Item Tax Template",
            "company": self.company.name,
            "title": "_Test Item Tax Template - sales/purchase decoupled tax accounts_" + unique_id,
            "taxes": [
                {
                    "tax_type": self.vat_sales_account.name,
                    "tax_rate": 10,
                    "transaction_type": "Sales"
                },
                {
                    "tax_type": self.vat_purchase_account.name,
                    "tax_rate": 10,
                    "transaction_type": "Purchase"
                },
            ]
        }).insert()

        # Create a second Item tax template with higher VAT rate
        self.item_tax_template_high_rate = frappe.get_doc({
            "doctype": "Item Tax Template",
            "company": self.company.name,
            "title": "_Test Item Tax Template - high rate - sales/purchase decoupled tax accounts_" + unique_id,
            "taxes": [
                {
                    "tax_type": self.vat_sales_account.name,
                    "tax_rate": 15,
                    "transaction_type": "Sales"
                },
                {
                    "tax_type": self.vat_purchase_account.name,
                    "tax_rate": 15,
                    "transaction_type": "Purchase"
                },
            ]
        }).insert()

        # Create sales tax template
        sales_taxes = [
                {
                    "charge_type": "On Net Total",
                    "account_head": self.vat_sales_account.name,
                    "description": "VAT 10%",
                    "cost_center": self.cost_center,
                    "rate": 10
                }
            ]
        self.sales_tax_template = frappe.get_doc({
            "doctype": "Sales Taxes and Charges Template",
            "company": self.company.name,
            "title": "_Test Sales Taxes and Charges Template - sales/purchase decoupled tax accounts_" + unique_id,
            "taxes": sales_taxes
        }).insert()

        # Create purchase tax template
        purchase_taxes = [
                {
                    "charge_type": "On Net Total",
                    "account_head": self.vat_purchase_account.name,
                    "description": "VAT 10%",
                    "cost_center": self.cost_center,
                    "rate": 10
                }
            ]
        self.purchase_tax_template = frappe.get_doc({
            "doctype": "Purchase Taxes and Charges Template",
            "company": self.company.name,
            "title": "_Test Purchase Taxes and Charges Template - sales/purchase decoupled tax accounts_" + unique_id,
            "taxes": purchase_taxes
        }).insert()

        # Create a new Item
        self.item = frappe.get_doc({
            "doctype": "Item",
            "item_code": "_Test Item - sales/purchase decoupled tax accounts_" + unique_id,
            "item_name": "_Test Item",
            "item_group": "All Item Groups",
            "taxes": [
                {
                    "item_tax_template": self.item_tax_template.name,
                }
            ]
        }).insert()

        # Create a second Item with higher VAT rate
        self.item2 = frappe.get_doc({
            "doctype": "Item",
            "item_code": "_Test Item2 - sales/purchase decoupled tax accounts_" + unique_id,
            "item_name": "_Test Item2",
            "item_group": "All Item Groups",
            "taxes": [
                {
                    "item_tax_template": self.item_tax_template_high_rate.name,
                }
            ]
        }).insert()

        # Create payment terms
        self.payment_terms = frappe.get_doc({
            "doctype": "Payment Terms Template",
            "title": "_Test Payment Terms_" + unique_id,
            "template_name": "_Test Payment Terms_" + unique_id,
            "terms": [{
                "payment_amount": 100,
                "invoice_portion": 100,
                "payment_type": "Percent",
                "due_date": 0
            }]
        }).insert()

        # Create a new Sales Invoice
        self.sales_invoice = frappe.get_doc({
            "doctype": "Sales Invoice",
            "name": "_Test Sales Invoice - sales/purchase decoupled tax accounts_" + unique_id,
            "customer": "_Test Customer",
            "currency": "CHF",
            "payment_terms": "_Test Payment Terms_" + unique_id,
            "cost_center": self.cost_center,
            "company": self.company.name,
            "taxes_and_charges": self.sales_tax_template.name,
            "taxes": sales_taxes,  # Need to be set manually since js is not executed.
            "items": [
                {
                    "item_code": self.item.item_code,
                    "qty": 1,
                    "rate": 100,
                    "cost_center": self.cost_center,
                },
                {
                    "item_code": self.item2.item_code,
                    "qty": 1,
                    "rate": 100,
                    "cost_center": self.cost_center,
                }
            ]
        }).insert()
        self.sales_invoice.submit()


        # Create a new Purchase Invoice
        self.purchase_invoice = frappe.get_doc({
            "doctype": "Purchase Invoice",
            "name": "_Test Purchase Invoice - sales/purchase decoupled tax accounts_" + unique_id,
            "supplier": "_Test Supplier",
            "currency": "CHF",
            "payment_terms": "_Test Payment Terms_" + unique_id,
            "cost_center": self.cost_center,
            "company": self.company.name,
            "taxes_and_charges": self.purchase_tax_template.name,
            "taxes": purchase_taxes,  # Need to be set manually since js is not executed.
            "items": [
                {
                    "item_code": self.item.item_code,
                    "qty": 1,
                    "rate": 100,
                    "cost_center": self.cost_center,
                },
                {
                    "item_code": self.item2.item_code,
                    "qty": 1,
                    "rate": 100,
                    "cost_center": self.cost_center,
                }
            ]
        }).insert()
        self.purchase_invoice.submit()

        
    def test_vat_sales_invoice(self):
        """Check that correct VAT is applied to Sales Invoice"""
        
        # Get general ledger entries
        gl_entries = frappe.get_all("GL Entry", fields=["account", "debit", "credit"],
                                                        filters={"voucher_no": self.sales_invoice.name})

        # Check that the VAT is taken correctly and affect the correct accounts
        entry_of_interest = list(filter(lambda x: x["account"] == self.vat_sales_account.name, gl_entries))

        # Assert that only one entry is found
        self.assertTrue(len(entry_of_interest) == 1)
        # Assert that the VAT is taken correctly at 25 CHF
        self.assertEqual(entry_of_interest[0]["debit"], 0)
        self.assertEqual(entry_of_interest[0]["credit"], 25)


    def test_vat_purchase_invoice(self):
        """Check that correct VAT is applied to Purchase Invoice"""
        
        # Get general ledger entries
        gl_entries = frappe.get_all("GL Entry", fields=["account", "debit", "credit"],
                                                        filters={"voucher_no": self.purchase_invoice.name})
        
        # Check that the VAT is taken correctly and affect the correct accounts
        entry_of_interest = list(filter(lambda x: x["account"] == self.vat_purchase_account.name, gl_entries))

        # Assert that only one entry is found
        self.assertTrue(len(entry_of_interest) == 1)
        # Assert that the VAT is taken correctly at 25 CHF
        self.assertEqual(entry_of_interest[0]["debit"], 25)
        self.assertEqual(entry_of_interest[0]["credit"], 0)

    def tearDown(self):
        frappe.db.rollback()
