import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate
from erpnext.accounts.report.share_ledger.share_ledger import execute

class TestShareLedger(FrappeTestCase):

    def setUp(self):
        from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
        create_company()
        if not frappe.db.exists("Shareholder", {"title": "_Test Shareholder"}):
            self.shareholder = frappe.get_doc({
                "doctype": "Shareholder",
                "title": "_Test Shareholder",
                "shareholder_name": "_Test Shareholder",
                "company": "_Test Company",
                "share_balance": [
                    {"title": "Equity", "share_type": "Equity", "no_of_shares": 10, "rate": 100, "amount": 1000, "from_no": 1, "to_no": 10},
                    {"title": "Preference", "share_type": "Preference", "no_of_shares": 5, "rate": 200, "amount": 1000, "from_no": 11, "to_no": 15}
                ]
            }).insert(ignore_permissions=True)
        else:
            shareholder_name = frappe.db.get_value("Shareholder", {"title": "_Test Shareholder"}, "name")
            self.shareholder = frappe.get_doc("Shareholder", shareholder_name)

        if not frappe.db.exists("Shareholder", {"title": "_Other Shareholder"}):
            self.other_shareholder = frappe.get_doc({
                "doctype": "Shareholder",
                "title": "_Other Shareholder",
                "company": "_Test Company",
                "shareholder_name": "_Other Shareholder"
            }).insert(ignore_permissions=True)
        else:
            shareholder_name = frappe.db.get_value("Shareholder", {"title": "_Other Shareholder"}, "name")
            self.other_shareholder = frappe.get_doc("Shareholder", shareholder_name)

        if not frappe.db.exists("Share Transfer", "TR-0001"):
            self.transfer = frappe.get_doc({
                "doctype": "Share Transfer",
                "share_type": "Equity",
                "transfer_type": "Transfer",
                "no_of_shares": 10,
                "rate": 100,
                "amount": 1000,
                "from_shareholder": self.shareholder.name,
                "to_shareholder": self.other_shareholder.name,
                "date": nowdate(),
                "company": "_Test Company",
                "equity_or_liability_account": "Equity - _TC",   
                "docstatus": 1,
                "from_no": 1,
                "to_no": 10 
            }).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.db.rollback()

    def test_execute_with_transfers_TC_ACC_569(self):
        filters = {"date": nowdate(), "shareholder": self.shareholder.name}
        columns, data = execute(filters)

        self.assertIsInstance(columns, list)
        self.assertGreater(len(columns), 0)
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)


        first_row = data[0]
        self.assertEqual(first_row[0], self.shareholder.name)
        self.assertEqual(first_row[3], "Equity")
        self.assertEqual(first_row[4], 10)  
        self.assertEqual(first_row[6], 1000)  
        self.assertIn("Transfer", first_row[2])

    def test_execute_without_shareholder_TC_ACC_570(self):
        filters = {"date": nowdate()}  
        columns, data = execute(filters)
        self.assertIsInstance(columns, list)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 0)

    def test_execute_missing_date_TC_ACC_571(self):
        filters = {"shareholder": "_Test Shareholder"}
        with self.assertRaises(frappe.exceptions.ValidationError):
            execute(filters)