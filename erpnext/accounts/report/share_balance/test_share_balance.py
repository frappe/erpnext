import frappe
from frappe.tests.utils import FrappeTestCase
from erpnext.accounts.report.share_balance.share_balance import execute
import frappe.utils

class TestShareBalance(FrappeTestCase):

    def setUp(self):
    
        if not frappe.db.exists("Shareholder", "_Test Shareholder"):
            self.shareholder = frappe.get_doc({
                "doctype": "Shareholder",
                "title": "_Test Shareholder",
                "shareholder_name": "_Test Shareholder",
                "share_balance": [
                    {
                        "title": "Equity",
                        "share_type": "Equity",
                        "no_of_shares": 10,
                        "rate": 100,
                        "amount": 1000,
                        "from_no": 1,
                        "to_no": 10
                    },
                    {
                        "title": "Preference",
                        "share_type": "Preference",
                        "no_of_shares": 5,
                        "rate": 200,
                        "amount": 1000,
                        "from_no": 11,
                        "to_no": 15
                    }
                ]
            }).insert(ignore_permissions=True)
        else:
            self.shareholder = frappe.get_doc("Shareholder", "_Test Shareholder")

    def tearDown(self):
       
        frappe.db.rollback()

    def test_execute_with_shareholder_TC_ACC_572(self):
        filters = {"date": frappe.utils.now(), "shareholder": self.shareholder.name}
        columns, data = execute(filters)


        self.assertIsInstance(columns, list)
        self.assertGreater(len(columns), 0)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)  

       
        expected_keys = [self.shareholder.name, "Equity", 10, 100, 1000]
        self.assertEqual(data[0], expected_keys)

        expected_keys2 = [self.shareholder.name, "Preference", 5, 200, 1000]
        self.assertEqual(data[1], expected_keys2)

    def test_execute_without_shareholder_TC_ACC_573(self):
        filters = {"date": "2025-10-01"}  
        columns, data = execute(filters)

        self.assertIsInstance(columns, list)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 0) 



    def test_execute_merges_share_type_updates_rate_TC_ACC_574(self):
        """Ensure multiple entries with same share_type merge and update rate"""
        shareholder = frappe.get_doc({
            "doctype": "Shareholder",
            "title": "_Test Merge Once Shareholder",
            "shareholder_name": "_Test Merge Once Shareholder",
            "share_balance": [
                {
                    "title": "Equity-1",
                    "share_type": "Equity",
                    "no_of_shares": 10,
                    "rate": 100,
                    "amount": 1000,
                    "from_no": 1,
                    "to_no": 10
                },
                {
                    "title": "Equity-2",
                    "share_type": "Equity",  # same type -> triggers merge block
                    "no_of_shares": 20,
                    "rate": 200,
                    "amount": 4000,
                    "from_no": 11,
                    "to_no": 30
                }
            ]
        }).insert(ignore_permissions=True)

        filters = {"date": frappe.utils.now(), "shareholder": shareholder.name}
        columns, data = execute(filters)

        # merged into one row
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0][1], "Equity")
        self.assertEqual(data[0][2], 30)    # shares merged: 10 + 20
        self.assertEqual(data[0][4], 5000)  # amount merged: 1000 + 4000
        self.assertAlmostEqual(data[0][3], 5000 / 30)  # rate updated correctly
        