import frappe
from frappe.tests.utils import FrappeTestCase
from erpnext.accounts.report.purchase_invoice_trends import purchase_invoice_trends
from frappe import _


class TestPurchaseInvoiceTrends(FrappeTestCase):
    def setUp(self):
        from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
        from erpnext.buying.doctype.purchase_order.test_purchase_order import get_or_create_fiscal_year

        create_company()
        get_or_create_fiscal_year("_Test Company")


    def test_purchase_invoice_trends_report_TC_ACC_585(self):
        from erpnext.accounts.utils  import get_fiscal_year
        year = get_fiscal_year(date=frappe.utils.now(), company="_Test Company")[0]
        filters = frappe._dict({
            "company": "_Test Company",         
            "fiscal_year": year, 
            "period": "Monthly",                
            "based_on": "Supplier",             
        })

        columns, data = purchase_invoice_trends.execute(filters)

        self.assertIsInstance(columns, list)
        self.assertIsInstance(data, list)

    def test_execute_with_different_period(self):
        from erpnext.accounts.utils  import get_fiscal_year

        year = get_fiscal_year(date=frappe.utils.now(), company="_Test Company")[0]
        
        filters = frappe._dict({
            "company": "_Test Company",        
            "fiscal_year": year,
            "period": "Quarterly",             
            "based_on": "Supplier",           
        })

        columns, data = purchase_invoice_trends.execute(filters)

        self.assertIsInstance(columns, list)
        self.assertIsInstance(data, list)
