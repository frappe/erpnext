import frappe
from frappe.tests.utils import FrappeTestCase
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.accounts.doctype.account.test_account import create_account, make_company, _make_test_records
from erpnext.accounts.doctype.payment_entry.test_payment_entry import get_or_create_fiscal_year
from erpnext.setup.doctype.company.test_company import create_child_company as create_company
from erpnext.accounts.report.cash_flow.cash_flow import execute

class TestCashFlow(FrappeTestCase, AccountsTestMixin):
    def setUp(self):

        # Create Transit warehouse type
        if not frappe.db.exists("Warehouse Type", "Transit"):
            frappe.get_doc(dict(
                doctype = "Warehouse Type",
                name = "Transit"
            )).insert(ignore_permissions=True)

        self.company_doc = make_company("_Test Company",is_group = False, abbr =  "_TC")

        self.company = self.company_doc.name

        self.bank_account = create_account(
            account_name="Receivable INR",
            parent_account="Current Assets - _TC",
            company=self.company,
            account_currency="INR",
        )
        create_account(
			account_name="Current Assets",
			is_group=1,
			parent_account="Application of Funds (Assets) - _TC",
			company=self.company,
		)

        create_account(
            account_name="Securities and Deposits",
            is_group=1,
            parent_account="Current Assets - _TC",
            company=self.company,
        )

        self.debtors_account = create_account(
            account_name="Earnest Money",
            parent_account="Securities and Deposits - _TC",
            company=self.company,
        )

    def tearDown(self):
        frappe.db.rollback()

    def test_cashflow_report_TC_ACC_593(self):
        # Ensure fiscal year is present
        get_or_create_fiscal_year(self.company)

        # Create a Journal Entry: Cash flows from Debtors to Bank (simulate collection)
        je = frappe.get_doc({
            "doctype": "Journal Entry",
            "voucher_type": "Bank Entry",
            "company": self.company,
            "posting_date": "2025-05-10",
            "accounts": [
                {
                    "account": self.bank_account,
                    "debit_in_account_currency": 10000,
                },
                {
                    "account": self.debtors_account,
                    "credit_in_account_currency": 10000,
                },
            ],
        })
        je.cheque_no = "Reference"
        je.cheque_date = frappe.utils.getdate()
        je.insert()
        je.submit()

        filters = frappe._dict({
            "company": self.company,
            "period_start_date": "2025-04-01",
            "period_end_date": "2025-10-31",
            "periodicity": "Quarterly",
            "presentation_currency": "INR",
        })

        columns, data, msg, chart, report_summary = execute(filters)
        # Basic assertion examples
        self.assertIsInstance(columns, list)
        self.assertIsInstance(data, list)
        self.assertIn('periodicity', filters)
        # Further assertions based on known test data
        self.assertTrue(len(columns) > 0, "Report should have at least one column.")
        self.assertTrue(isinstance(chart, dict) or chart is None)
        self.assertTrue(isinstance(report_summary, list) or isinstance(report_summary, dict))
