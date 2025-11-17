import frappe
from frappe.tests.utils import FrappeTestCase
from frappe import _dict
from unittest.mock import patch, MagicMock
from erpnext.accounts.report.open_item import open_item
from datetime import date


class TestOpenItem(FrappeTestCase):
    def get_filters(self):
        return _dict({
            "company": "Test Co",
            "from_date": "2024-01-01",
            "to_date": "2024-12-31",
        })

    def test_execute_without_filters_TC_ACC_435(self):
        cols, res = open_item.execute(None)
        self.assertEqual(cols, [])
        self.assertEqual(res, [])

    def test_execute_with_account_currency_TC_ACC_436(self):
        f = self.get_filters()
        f.print_in_account_currency = 1
        f.account = None
        with self.assertRaises(Exception):
            open_item.execute(f)

    def test_validate_filters_variants_TC_ACC_437(self):
        with self.assertRaises(Exception):
            open_item.validate_filters(_dict({}), {})

        # invalid account -> stringified list
        f = self.get_filters()
        f.account = '["NonExisting"]'
        with self.assertRaises(Exception):
            open_item.validate_filters(f, {})

        # child account with group by
        f = self.get_filters()
        f.account = '["Acc1"]'
        f.group_by = "Group by Account"
        with self.assertRaises(Exception):
            open_item.validate_filters(f, {"Acc1": _dict(is_group=0)})

        # voucher conflict
        f = self.get_filters()
        f.voucher_no = "VN1"
        f.group_by = "Group by Voucher"
        with self.assertRaises(Exception):
            open_item.validate_filters(f, {})

        # invalid date range
        f = self.get_filters()
        f.from_date = "2025-01-01"
        f.to_date = "2024-01-01"
        with self.assertRaises(Exception):
            open_item.validate_filters(f, {})

        # valid project & cost_center
        f = self.get_filters()
        f.project = '["P1"]'
        f.cost_center = '["CC1"]'
        open_item.validate_filters(f, {})

    def test_validate_party_variants_TC_ACC_438(self):
        f = self.get_filters()
        f.party_type = "Customer"
        f.party = ["X1"]

        frappe.db.exists = MagicMock(return_value=False)
        with self.assertRaises(Exception):
            open_item.validate_party(f)

        frappe.db.exists = MagicMock(return_value=True)
        open_item.validate_party(f)

    def test_set_account_currency_variants_TC_ACC_439(self):
        # multiple accounts same currency
        f = self.get_filters()
        f.account = ["A1", "A2"]
        with patch("erpnext.accounts.report.open_item.open_item.get_account_currency", return_value="USD"):
            with patch("frappe.get_cached_value", return_value="INR"):
                res = open_item.set_account_currency(f)
                self.assertIn("account_currency", res)

        # party_type branch
        f = self.get_filters()
        f.party = ["C1"]
        f.party_type = "Customer"
        with patch("frappe.get_cached_value", return_value="INR"):
            with patch("frappe.db.get_value", return_value=None):
                res = open_item.set_account_currency(f)
                self.assertIn("account_currency", res)

    def test_get_unreconciled_reconciled_totals_TC_ACC_440(self):
        gle = [
            {"is_reconciled": 1, "credit": 1, "credit_in_account_currency": 10, "debit": 1, "debit_in_account_currency": 5},
            {"is_reconciled": 0, "credit": 1, "credit_in_account_currency": 2, "debit": 1, "debit_in_account_currency": 3},
        ]
        res = open_item.get_unreconciled_reconciled_totals(gle)
        self.assertEqual(res[0]["credit"], 10)
        self.assertEqual(res[1]["debit"], 3)

        r1 = _dict(is_reconciled=1, credit=1, debit=1, credit_in_account_currency=5, debit_in_account_currency=4)
        r2 = _dict(is_reconciled=0, credit=1, debit=1, credit_in_account_currency=2, debit_in_account_currency=1)
        rr1 = open_item.get_unreconciled_reconciled_totals_other(r1)
        rr2 = open_item.get_unreconciled_reconciled_totals_other(r2)
        self.assertEqual(rr1[0]["credit"], 5)
        self.assertEqual(rr2[1]["credit"], 2)

    def test_get_conditions_and_gl_entries_TC_ACC_441(self):
        f = self.get_filters()
        f.account = "Acc1,Acc2"
        f.cost_center = ["CC1"]
        f.voucher_no, f.against_voucher_no = "VN1", "AV1"
        f.ignore_err = 1
        f.voucher_no_not_in = ["X1"]
        f.group_by, f.party, f.party_type = "Group by Party", ["C1"], "Customer"
        f.show_unreconciled_entries, f.show_reconciled_entries = 1, 1
        f.finance_book, f.company_fb = "FB1", "CFB1"
        f.include_default_book_entries = 0
        f.include_dimensions = 1
        f.add_values_in_transaction_currency = 1
        f.show_remarks = 1
        f.presentation_currency = "USD"

        fake_gl_row = {
            "name": "GL1",
            "posting_date": "2024-06-01",
            "account": "Acc1",
            "debit": 100,
            "credit": 0,
            "remarks": "ok",
        }

        with patch("erpnext.accounts.report.open_item.open_item.get_accounts_with_children", return_value=["Acc1", "Acc2"]), \
            patch("erpnext.accounts.report.open_item.open_item.get_cost_centers_with_children", return_value=["CC1"]), \
            patch("erpnext.accounts.report.open_item.open_item.get_accounting_dimensions",
                return_value=[_dict(fieldname="dim1", disabled=0, document_type="Cost Center")]), \
            patch("frappe.db.get_all", return_value=[["JV-1"]]), \
            patch("frappe.db.get_value", return_value="INR"), \
            patch("frappe.get_cached_value", return_value=0), \
            patch("frappe.desk.reportview.build_match_conditions", return_value="(company='Test Co')"), \
            patch("erpnext.accounts.report.open_item.open_item.convert_to_presentation_currency",
                side_effect=lambda f, rows: rows), \
            patch("frappe.db.get_single_value", side_effect=[500, None]), \
            patch("frappe.db.sql", side_effect=[
                [fake_gl_row],                 
                [{"remarks": "X"*600}],        
                [{"remarks": "ok"}],          
                []                            
            ]):

            cond = open_item.get_conditions(f, 0)
            self.assertIn("account", cond)

            rows = open_item.get_gl_entries(
                f, accounting_dimensions=["dim1"]
            )
            self.assertIsInstance(rows, dict)

    def test_group_by_field_balance_columns_TC_ACC_442(self):
        self.assertEqual(open_item.group_by_field("Group by Party"), "party")
        self.assertEqual(open_item.group_by_field("Group by Account"), "account")
        self.assertEqual(open_item.group_by_field("X"), "voucher_no")

        bal = open_item.get_balance({"debit": 5, "credit": 2}, 0, "debit", "credit")
        self.assertEqual(bal, 3)

        f = self.get_filters()
        f.add_values_in_transaction_currency = 1
        f.include_dimensions = 0
        f.show_remarks = 1
        with patch("erpnext.accounts.report.open_item.open_item.get_company_currency", return_value="USD"):
            cols = open_item.get_columns(f)
            self.assertTrue(any("Debit (Transaction)" in c.get("label", "") for c in cols))
            self.assertTrue(any("Remarks" in c.get("label", "") for c in cols))
    
    def test_execute_and_data_with_opening_closing_paths_TC_ACC_443(self):
        
        f = self.get_filters()
        f.group_by = "Group by Voucher"
        f.include_dimensions = 0
        f.from_date = "2024-05-01"
        f.to_date = "2024-06-30"

        fake_gl_entry = frappe._dict({
            "name": "GL-001",
            "posting_date": date(2024, 6, 1),  
            "account": "Acc1",
            "voucher_no": "VN-1",
            "voucher_type": "Sales Invoice",
            "debit": 100,
            "credit": 0,
            "debit_in_account_currency": 100,
            "credit_in_account_currency": 0,
            "debit_in_transaction_currency": 100,
            "credit_in_transaction_currency": 0,
            "is_reconciled": 1,
            "is_opening": "No",                
            "against_voucher": None,
        })

        def fake_sql(query, *args, **kwargs):
            q = str(query)
            if "from tabAccount" in q or "from `tabAccount`" in q:
                return [frappe._dict({"name": "Acc1", "is_group": 1})]
            if "from `tabGL Entry`" in q or "from tabGL Entry" in q:
                return [fake_gl_entry]
            if "from `tabPurchase Invoice`" in q:
                return [frappe._dict({"name": "VN-1", "bill_no": "BILL-001"})]
            return []

        with patch("frappe.db.sql", side_effect=fake_sql), \
            patch("frappe.db.get_single_value", return_value=None), \
            patch("frappe.desk.reportview.build_match_conditions", return_value=""), \
            patch("erpnext.accounts.report.open_item.open_item.get_accounting_dimensions", return_value=[]), \
            patch("frappe.db.exists", return_value=True):

            cols, res = open_item.execute(f)

            self.assertGreater(len(res), 0)

    def test_get_accountwise_gle_variants_TC_ACC_444(self):
        f = self.get_filters()
        f.group_by = "Group by Voucher (Consolidated)"  
        f.show_opening_entries = 1
        f.include_dimensions = 0

        gle = frappe._dict({
            "posting_date": date(2024, 6, 1),
            "voucher_type": "Sales Invoice",
            "voucher_no": "VN-1",
            "account": "Acc1",
            "party_type": "Customer",
            "party": "P1",
            "debit": 50,
            "credit": 0,
            "debit_in_account_currency": 50,
            "credit_in_account_currency": 0,
            "debit_in_transaction_currency": 50,
            "credit_in_transaction_currency": 0,
            "is_reconciled": 1,
            "against_voucher": "AG1",
            "is_opening": "No",
            "creation": "2024-06-01",
        })

        totals_dict = open_item.get_totals_dict()
        gle_map = open_item.initialize_gle_map([gle], f, totals_dict)

        with patch("frappe.db.get_single_value", return_value=0):
            totals, entries = open_item.get_accountwise_gle(f, [], [gle], gle_map, totals_dict)
            self.assertTrue(any(e.get("voucher_no") == "VN-1" for e in entries))

    def test_get_result_as_list_variants_TC_ACC_445(self):
        f = self.get_filters()
        f.account_currency = "INR"

        reconciled_row = {"account": "Acc1", "debit": 10, "credit": 0, "is_reconciled": 1}
        unreconciled_row = {"account": "Acc1", "debit": 0, "credit": 5, "is_reconciled": 0}
        no_account_row = {"account": None, "debit": 2, "credit": 1, "is_reconciled": None}

        with patch("frappe.db.exists", return_value=True), \
             patch("erpnext.accounts.report.open_item.open_item.get_supplier_invoice_details",
                   return_value={"VN-1": "BILL-123"}):

            rows = open_item.get_result_as_list([reconciled_row, unreconciled_row, no_account_row], f)

        self.assertIn("reconciled", rows[0])
        self.assertIn("reconciled", rows[1])


    def test_get_accounts_with_children_branch_TC_ACC_446(self):
        doctype = frappe.qb.DocType("Account")

        with patch("frappe.qb.from_", return_value=frappe.qb.from_(doctype)):
            res = open_item.get_accounts_with_children(["Acc1"])
            self.assertIsNotNone(res)

    def test_execute_full_flow_TC_ACC_447(self):
        """Full-flow test covering execute → get_result → get_data_with_opening_closing → get_accountwise_gle → get_result_as_list"""
        
        if not frappe.db.exists("DocType", "Accounting Dimension"):
            self.skipTest("Accounting Dimension doctype not available")
        
        # Create a mock accounting dimension if needed
        if not frappe.db.exists("Accounting Dimension", "Cost Center"):
            try:
                dim = frappe.get_doc({
                    "doctype": "Accounting Dimension",
                    "document_type": "Cost Center",
                    "dimension_name": "Cost Center",
                    "disabled": 0
                })
                dim.insert(ignore_permissions=True)
            except Exception:
                self.skipTest("Could not create Accounting Dimension")

        # Filters that activate multiple branches
        filters = frappe._dict({
            "company": "_Test Company",
            "from_date": "2024-04-01",
            "to_date": "2024-04-30",
            "group_by": "Group by Voucher (Consolidated)",
            "include_dimensions": 0,
            "show_opening_entries": 1,
            "add_values_in_transaction_currency": 1,
            "show_net_values_in_party_account": 1,
        })

        # Create test data in the database instead of mocking
        self.create_test_data()

        cols, data = open_item.execute(filters)
        
        # ---------------- assertions ----------------
        self.assertIsInstance(cols, list)
        self.assertIsInstance(data, list)
        self.assertTrue(len(cols) > 0)
        self.cleanup_test_data()

    def create_test_data(self):
        """Create actual test data in the database"""
        # Create test accounts
        accounts = [
            {
                "doctype": "Account",
                "account_name": "_Test Open Item Account",
                "parent_account": "Accounts Receivable - _TC",
                "company": "_Test Company",
                "account_type": "Receivable"
            },
            {
                "doctype": "Account", 
                "account_name": "_Test Open Item Income",
                "parent_account": "Direct Income - _TC",
                "company": "_Test Company",
                "account_type": "Income Account"
            }
        ]
        
        for acc in accounts:
            if not frappe.db.exists("Account", acc["account_name"] + " - _TC"):
                frappe.get_doc(acc).insert(ignore_permissions=True)
        
        # Create test customer
        if not frappe.db.exists("Customer", "_Test Open Item Customer"):
            customer = frappe.get_doc({
                "doctype": "Customer",
                "customer_name": "_Test Open Item Customer",
                "customer_type": "Individual"
            })
            customer.insert(ignore_permissions=True)
        
        # Create test sales invoice
        if not frappe.db.exists("Sales Invoice", "_TEST-OPEN-ITEM-001"):
            sales_invoice = frappe.get_doc({
                "doctype": "Sales Invoice",
                "company": "_Test Company",
                "customer": "_Test Open Item Customer",
                "due_date": "2024-04-15",
                "posting_date": "2024-04-10",
                "items": [{
                    "item_code": "_Test Item",
                    "qty": 1,
                    "rate": 1000,
                    "income_account": "_Test Open Item Income - _TC"
                }],
                "taxes": []
            })
            sales_invoice.insert(ignore_permissions=True)
            sales_invoice.submit()

    def cleanup_test_data(self):
        """Clean up test data"""
        # Delete test sales invoice
        if frappe.db.exists("Sales Invoice", "_TEST-OPEN-ITEM-001"):
            doc = frappe.get_doc("Sales Invoice", "_TEST-OPEN-ITEM-001")
            if doc.docstatus == 1:
                doc.cancel()
            doc.delete(ignore_permissions=True)
        
        # Delete test accounts
        accounts_to_delete = [
            "_Test Open Item Account - _TC",
            "_Test Open Item Income - _TC"
        ]
        
        for account in accounts_to_delete:
            if frappe.db.exists("Account", account):
                frappe.delete_doc("Account", account, ignore_permissions=True)
        
        # Delete test customer
        if frappe.db.exists("Customer", "_Test Open Item Customer"):
            frappe.delete_doc("Customer", "_Test Open Item Customer", ignore_permissions=True)
