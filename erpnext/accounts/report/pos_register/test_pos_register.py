import frappe
from frappe.tests.utils import FrappeTestCase
from .pos_register import execute
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.doctype.pos_profile.test_pos_profile import make_pos_profile
from erpnext.selling.doctype.customer.test_customer import get_customer_dict_new
from erpnext.accounts.doctype.account.test_account import create_account, make_company
from erpnext.accounts.doctype.payment_entry.test_payment_entry import get_or_create_fiscal_year
from erpnext.accounts.doctype.pos_profile.test_pos_profile import make_pos_profile
from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_customer

class TestPOSRegistry(FrappeTestCase, AccountsTestMixin):

    def setUp(self):
        self.company = "_Test Company"
        make_company(self.company,is_group = False, abbr =  "_TC")
        
        # Ensure fiscal year exists
        get_or_create_fiscal_year(self.company)

        # Create test customer
        self.customer = create_customer("_Test POS Customer", "INR")

        # self.customer = frappe.get_doc(get_customer_dict_new("_Test POS Customer")).insert()

        # Create test bank and income accounts if not exists
        create_account(
            account_name="Bank",
            parent_account="Bank Accounts - _TC",
            account_type="Bank",
            company=self.company,
            is_group=0,
        )

        create_account(
            account_name="Sales",
            parent_account="Income - _TC",
            account_type="Income Account",
            company=self.company,
            is_group=0,
        )
        expense_account = frappe.db.get_value("Account", {"company": self.company, "account_type" : "Expense Account"}, "name")
        
        # Create POS Profile
        if not frappe.db.exists("Price List", "Test Price List"):
            frappe.get_doc(
                {
                    "doctype": "Price List",
                    "price_list_name": "Test Price List1",
                    "buying": 1,
                    "selling": 1,
                    "enabled": 0,
                }
            ).insert()
        self.create_dependencies_record()
        self.pos_profile = make_pos_profile(
            company=self.company,
            name="_Test POS Profile",
            customer=self.customer,
            income_account="Sales - _TC",
            payments=[{"mode_of_payment": "Cash"}],
            warehouse= frappe.db.get_value("Warehouse", {"company": self.company}, "name"),
            expense_account = expense_account
        )

    def tearDown(self):
        frappe.db.rollback()
        
    def create_dependencies_record(self, company="_Test Company"):
        """Create all dependent records needed for POS Profile test."""

        # 2. Warehouse
        if not frappe.db.exists("Warehouse", {"company": company}):
            frappe.get_doc({
                "doctype": "Warehouse",
                "warehouse_name": "_Test Warehouse",
                "company": company
            }).insert(ignore_permissions=True)

        parent_cc = frappe.db.get_value("Cost Center", {"company": company, "is_group": 1}, "name")
        if not parent_cc:
            # Create root cost center if missing
            root_cc = frappe.get_doc({
                "doctype": "Cost Center",
                "cost_center_name": f"{company} - Root",
                "is_group": 1,
                "company": company
            }).insert(ignore_permissions=True)
            parent_cc = root_cc.name

        # 3. Child Cost Centers
        for cc_name in ["_Test Cost Center", "_Test Write Off Cost Center"]:
            full_name = f"{cc_name} - _TC"
            if not frappe.db.exists("Cost Center", full_name):
                frappe.get_doc({
                    "doctype": "Cost Center",
                    "cost_center_name": cc_name,
                    "company": company,
                    "is_group": 0,
                    "parent_cost_center": parent_cc
                }).insert(ignore_permissions=True)

        #Price List
        if not frappe.db.exists("Price List", "_Test Price List"):
            frappe.get_doc({
                "doctype": "Price List",
                "price_list_name": "_Test Price List",
                "selling": 1,
                "enabled": 1,
                "currency": "INR"
            }).insert(ignore_permissions=True)

        # Account Creation 
        expense_root = frappe.db.get_value(
            "Account", {"account_type": "Expense Account", "is_group": 1, "company": company}, "name"
        ) or frappe.db.get_value(
            "Account", {"root_type": "Expense", "is_group": 1, "company": company}, "name"
        )
        if not expense_root:
            # fallback: manually create an "Expenses" group if missing
            expense_root = frappe.get_doc({
                "doctype": "Account",
                "account_name": "Expenses",
                "is_group": 1,
                "root_type": "Expense",
                "report_type": "Profit and Loss",
                "company": company,
            }).insert(ignore_permissions=True).name

        # create leaf accounts under the group
        for acc_name, acc_type in [
            ("_Test Account Cost for Goods Sold - _TC", "Cost of Goods Sold"),
            ("_Test Write Off - _TC", "Write Off"),
        ]:
            if not frappe.db.exists("Account", acc_name):
                frappe.get_doc({
                    "doctype": "Account",
                    "account_name": acc_name.split(" - ")[0],
                    "company": company,
                    "is_group": 0,
                    "root_type": "Expense",
                    "parent_account": expense_root,
                    "report_type": "Profit and Loss",
                    "account_type": "Indirect Expense"
                }).insert(ignore_permissions=True)

    def test_pos_registry_report_TC_ACC_594(self):
        pos_profile = make_pos_profile()
        # Create and submit POS invoice
        self.invoice = create_sales_invoice(
            customer=self.customer,
            company=self.company,
            pos_profile=pos_profile.name,
            is_pos=1,
            do_not_submit=True,
        )

        self.invoice.cash_bank_account = "Bank - _TC"
        self.invoice.paid_amount = 1000
        self.invoice.set("payments", [{"mode_of_payment": "Cash", "amount": 1000}])
        self.invoice.submit()

        filters = frappe._dict({
            "company": self.company,
            'from_date' :'2025-01-01',
            'to_date' :'2025-10-08',
            'group_by' :'POS Profile'
        })
        columns, data = execute(filters)

        # Assertions
        self.assertTrue(len(data) > 0, "POS Registry should return at least one row")

        # Verify payments
        for row in data:
            self.assertEqual(row.get("mode_of_payment"), "Cash")

    def test_pos_registry_filters_conditions_TC_ACC_595(self):
        filters = frappe._dict({})
        columns, data = execute(filters)
        self.assertTrue(len(data) == 0, "POS Registry should return no rows when no filters are applied")


        filters = frappe._dict({
            "pos_profile" : "Non-Existent POS Profile",
        })
        with self.assertRaisesRegex(frappe.ValidationError, "Company is mandatory"):
            columns, data = execute(filters)
        
        filters = frappe._dict({
            "pos_profile" : "Non-Existent POS Profile",
            "company" : "_Test Company",
        })
        with self.assertRaisesRegex(frappe.ValidationError, "From Date and To Date are mandatory"):
            columns, data = execute(filters)
        
        return
