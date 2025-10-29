import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today
from frappe import _dict
from erpnext.accounts.report.profitability_analysis import profitability_analysis as report


class TestProfitabilityAnalysis(FrappeTestCase):

    def setUp(self):
        from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
        from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
        from erpnext.buying.doctype.purchase_order.test_purchase_order import get_or_create_fiscal_year, validate_fiscal_year
        from erpnext.accounts.doctype.account.test_account import create_account

        # Setup company, fiscal year, cost center
        create_company()
        get_or_create_fiscal_year("_Test Company")
        create_cost_center(cost_center_name="_Test Cost Center", company="_Test Company")
        self.company = "_Test Company"
        self.from_date = add_days(today(), -30)
        self.to_date = today()

        # Get cost center
        self.cost_center = frappe.db.get_value(
            "Cost Center", {"company": self.company, "cost_center_name": "_Test Cost Center"}
        )

        # Create a test project
        if not frappe.db.exists("Project", {"project_name": "Test Project", "company": self.company}):
            frappe.get_doc({
                "doctype": "Project",
                "project_name": "Test Project",
                "company": self.company,
            }).insert(ignore_if_duplicate=True)
        self.project = frappe.db.get_value("Project", {"project_name": "Test Project"})

        # Create an expense account
        create_account(
            account_name="Test Expense",
            parent_account="Expenses - _TC",
            company=self.company,
        )
        self.expense_account = frappe.db.get_value("Account", {"company": self.company, "account_name": "Test Expense"})

        # Create a Journal Entry
        asset_account = frappe.db.get_value("Account", {"company": self.company, "root_type": "Asset"})
        jv = frappe.get_doc({
            "doctype": "Journal Entry",
            "voucher_type": "Journal Entry",
            "posting_date": today(),
            "company": self.company,
            "accounts": [
                {
                    "account": self.expense_account,
                    "debit_in_account_currency": 1000,
                    "credit_in_account_currency": 0,
                    "cost_center": self.cost_center,
                    "project": self.project,
                },
                {
                    "account": asset_account,
                    "debit_in_account_currency": 0,
                    "credit_in_account_currency": 1000,
                }
            ]
        })
        jv.insert(ignore_permissions=True)
        jv.submit()

    # ------------------ Report Execution Tests ------------------

    def test_execute_with_cost_center_TC_ACC_575(self):
        from erpnext.accounts.utils import get_fiscal_year
        filters = _dict({
            "based_on": "Cost Center",
            "company": self.company,
            "from_date": self.from_date,
            "to_date": self.to_date,
            "fiscal_year": get_fiscal_year(date=self.from_date, company=self.company)[0]
        })
        cols, data = report.execute(filters)

        self.assertTrue(any(c["fieldname"] == "income" for c in cols))
        self.assertTrue(any(d.get("account") == self.cost_center for d in data))
        self.assertTrue(any("Total" in str(d.get("account")) for d in data))

    def test_execute_with_project_TC_ACC_576(self):
        from erpnext.accounts.utils import get_fiscal_year
        fiscal_year = get_fiscal_year(date=self.from_date, company=self.company)
        year = fiscal_year[0] if fiscal_year else "_Test Fiscal Year"
        filters = _dict({
            "based_on": "Project",
            "company": self.company,
            "from_date": self.from_date,
            "to_date": self.to_date,
            "fiscal_year": year
        })
        cols, data = report.execute(filters)
        self.assertTrue(any(d.get("account") == self.project for d in data))

    def test_execute_with_accounting_dimension_validation_TC_ACC_577(self):
        filters = _dict({
            "based_on": "Accounting Dimension",
            "accounting_dimension": None,
            "company": self.company,
            "from_date": self.from_date,
            "to_date": self.to_date,
        })
        with self.assertRaises(frappe.ValidationError):
            report.execute(filters)

    # ------------------ Accounts Data Tests ------------------

    def test_get_accounts_data_cost_center_TC_ACC_578(self):
        data = report.get_accounts_data("Cost Center", self.company)
        self.assertTrue(any(d["name"] == self.cost_center for d in data))

    def test_get_accounts_data_project_TC_ACC_579(self):
        data = report.get_accounts_data("Project", self.company)
        self.assertTrue(any(d["name"] == self.project for d in data))

    def test_get_columns_structure_TC_ACC_580(self):
        filters = _dict({"based_on": "Cost Center"})
        cols = report.get_columns(filters)
        self.assertIn("account", [c["fieldname"] for c in cols])

    # ------------------ GL Entry Tests ------------------

    def test_set_gl_entries_by_account_TC_ACC_581(self):
        gl_map = report.set_gl_entries_by_account(
            self.company, self.from_date, self.to_date, "cost_center", {}
        )
        self.assertIn(self.cost_center, gl_map)
        self.assertTrue(any(e.debit == 1000 for e in gl_map[self.cost_center]))

    # ------------------ Calculate and Accumulate Tests ------------------

    def test_calculate_and_accumulate_TC_ACC_582(self):
        accounts = [_dict({
            "name": self.cost_center,
            "parent_account": None,
            "account_name": self.expense_account
        })]

        gl_map = {
            self.cost_center: [
                frappe._dict({"type": "Expense", "debit": 500, "credit": 0, "is_opening": "No"})
            ]
        }

        # calculate values
        total_row = report.calculate_values(accounts, gl_map, _dict())
        self.assertEqual(accounts[0]["expense"], 500)
        self.assertEqual(total_row["expense"], 500)

        # accumulate into parent
        parent = _dict({"name": "Parent CC", "parent_account": None, "account_name": "Parent", "expense": 0.0, "income": 0.0, "gross_profit_loss": 0.0})
        accounts_by_name = {self.cost_center: accounts[0], "Parent CC": parent}
        accounts[0]["parent_account"] = "Parent CC"
        report.accumulate_values_into_parents(accounts, accounts_by_name)
        self.assertEqual(parent["expense"], 500)

    # ------------------ Prepare Data Test ------------------

    def test_prepare_profitability_analysis_report_data_TC_ACC_583(self):
        accounts = [_dict({
            "name": self.cost_center,
            "parent_account": None,
            "account_name": self.expense_account,
            "indent": 0,
            "income": 200,
            "expense": 100,
            "gross_profit_loss": 100,
        })]
        total_row = _dict({"income": 200, "expense": 100, "gross_profit_loss": 100, "account": "'Total'", "account_name": "'Total'"})
        parent_map = {}
        data = report.prepare_data(accounts, _dict({"company": self.company, "fiscal_year": "2024-25"}), total_row, parent_map, "Cost Center")
        self.assertTrue(any(r.get("account") == self.cost_center for r in data))
        self.assertTrue(any("Total" in str(r.get("account")) for r in data))
