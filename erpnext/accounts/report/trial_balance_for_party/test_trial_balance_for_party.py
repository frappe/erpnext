import frappe
from frappe.utils.data import add_days, nowdate
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt, today
from erpnext.accounts.report.trial_balance_for_party.trial_balance_for_party import (
    execute,
    get_columns,
    get_balances_within_period,
    is_party_name_visible,
    get_opening_balances
)

class TestTrialBalanceForParty(FrappeTestCase):
    def setUp(self):
        from erpnext.accounts.doctype.account.test_account import create_account
        from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_company, create_customer
        from erpnext.accounts.doctype.payment_entry.test_payment_entry import  get_or_create_fiscal_year
		
        create_company(company_name = "_Test Company")
        self.company = "_Test Company"
        self.fiscal_year = get_or_create_fiscal_year()
        self.customer = create_customer(customer_name="_Test Customer", company="_Test Company")
        parent_account = frappe.db.get_value(
            "Account",
            {"company": self.company, "is_group": 1},
            "name"
        )
        
        self.account1 = create_account(
            account_name="Test Account TBP", 
            account_type="Cash", 
            parent_account=parent_account, 
            company=self.company
        )
        
        self.account2 = create_account(
            account_name="Test Account A TBP", 
            account_type="Cash", 
            parent_account=parent_account, 
            company=self.company
        )
    
    def test_execute_with_customer_filters_TC_ACC_589(self):
        filters = frappe._dict({
            "company": self.company,
            "fiscal_year": self.fiscal_year,
            "party_type": "Customer",
            "show_zero_values": 1
        })

        columns, data = execute(filters)

        self.assertIsInstance(columns, list)
        self.assertIsInstance(data, list)
        self.assertTrue(any(col["fieldname"] == "party" for col in columns))
        self.assertTrue(any(col["fieldname"] == "opening_debit" for col in columns))

        self.assertEqual(data[-1]["party"], "'Totals'")

        # Check party_name column added if visible
        show_party_name = is_party_name_visible(filters)
        if show_party_name:
            self.assertTrue(any(col["fieldname"] == "party_name" for col in columns))

    def test_get_columns_explicit_TC_ACC_590(self):
        filters = frappe._dict({"party_type": "Customer"})
        # Case when party_name is visible
        columns = get_columns(filters, show_party_name=True)
        self.assertTrue(any(col["fieldname"] == "party_name" for col in columns))

        # Case when party_name is hidden
        columns = get_columns(filters, show_party_name=False)
        self.assertFalse(any(col["fieldname"] == "party_name" for col in columns))
       
    def test_get_opening_balances_TC_ACC_591(self):
        from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
        account1 = self.account1
        account2 = self.account2 

        make_journal_entry(
            account1=account1,
            account2=account2,
            amount=1000,   
            posting_date=today(),
            submit=True
        )

        filters = frappe._dict({
            "company": self.company,
            "fiscal_year": self.fiscal_year,
            "party_type": "Customer"
        })

        opening_balances = get_opening_balances(filters)

    def test_get_balances_within_period_TC_ACC_592(self):
        from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
        account1 = self.account1
        account2 = self.account2

        make_journal_entry(
            account1=account1,
            account2=account2,
            amount=1000,
            posting_date=add_days(today(), -1), 
            save=True,
            submit=True
        )

        filters = frappe._dict({
            "company": self.company,
            "fiscal_year": self.fiscal_year,
            "party_type": "Customer",
            "from_date": add_days(today(), -5),
            "to_date": add_days(today(), 5)
        })

        balances = get_balances_within_period(filters)

        party_name = self.customer.name
        debit, credit = balances.get(party_name, [0, 0])