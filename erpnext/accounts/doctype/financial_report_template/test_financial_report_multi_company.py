import json

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt

from erpnext.accounts.doctype.financial_report_template.financial_report_engine import (
	FinancialReportEngine,
)


class TestFinancialReportEngineMultiCompany(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		cls.company_a = cls._ensure_company("Consolidated Report Test A", "CRTA", "INR")
		cls.company_b = cls._ensure_company("Consolidated Report Test B", "CRTB", "INR")
		cls.company_c = cls._ensure_company("Consolidated Report Test C", "CRTC", "USD")
		for company in (cls.company_a, cls.company_b, cls.company_c):
			cls._ensure_company_in_fiscal_year(company, "_Test Fiscal Year 2027")
		cls.create_test_template()

	@staticmethod
	def _ensure_company(company_name: str, abbr: str, currency: str) -> str:
		if frappe.db.exists("Company", company_name):
			return company_name

		company = frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": company_name,
				"abbr": abbr,
				"country": "India" if currency == "INR" else "United States",
				"default_currency": currency,
				"create_chart_of_accounts_based_on": "Standard Template",
				"chart_of_accounts": "Standard",
			}
		).insert()

		return company.name

	@staticmethod
	def _ensure_company_in_fiscal_year(company: str, fiscal_year_name: str):
		fiscal_year = frappe.get_doc("Fiscal Year", fiscal_year_name)
		linked_companies = {row.company for row in fiscal_year.companies}

		if company not in linked_companies:
			fiscal_year.append("companies", {"company": company})
			fiscal_year.save()

	@staticmethod
	def _get_accounts(
		company: str, root_type: str, limit: int = 1, exclude_account_types: list[str] | None = None
	):
		filters = {"company": company, "root_type": root_type, "is_group": 0, "disabled": 0}

		if exclude_account_types:
			filters["account_type"] = ["not in", exclude_account_types]

		return frappe.get_all("Account", filters=filters, pluck="name", order_by="lft", limit=limit)

	@staticmethod
	def _make_account_filter(company: str, account: str) -> str:
		account_name = frappe.db.get_value("Account", account, "account_name")
		return json.dumps({"and": [["company", "=", company], ["account_name", "=", account_name]]})

	@staticmethod
	def _get_cost_center(company: str) -> str:
		return frappe.get_all(
			"Cost Center", filters={"company": company, "is_group": 0}, pluck="name", order_by="lft", limit=1
		)[0]

	@classmethod
	def _make_journal_entry(
		cls, company: str, account1: str, account2: str, amount: float, posting_date: str
	):
		cost_center = cls._get_cost_center(company)
		journal_entry = frappe.new_doc("Journal Entry")
		journal_entry.posting_date = posting_date
		journal_entry.company = company
		journal_entry.user_remark = "test"
		journal_entry.multi_currency = 1
		journal_entry.set(
			"accounts",
			[
				{
					"account": account1,
					"cost_center": cost_center,
					"debit_in_account_currency": amount if amount > 0 else 0,
					"credit_in_account_currency": abs(amount) if amount < 0 else 0,
					"exchange_rate": 1,
				},
				{
					"account": account2,
					"cost_center": cost_center,
					"credit_in_account_currency": amount if amount > 0 else 0,
					"debit_in_account_currency": abs(amount) if amount < 0 else 0,
					"exchange_rate": 1,
				},
			],
		)
		journal_entry.insert()
		journal_entry.submit()
		return journal_entry

	@staticmethod
	def _get_period_key(columns: list[dict]) -> str:
		for column in columns:
			if column.get("fieldtype") == "Currency" and column.get("fieldname") != "total":
				return column["fieldname"]

		raise AssertionError("No period column found in custom financial report output")

	@classmethod
	def create_test_template(cls):
		if not frappe.db.exists("Financial Report Template", "Test P&L Template"):
			frappe.get_doc(
				{
					"doctype": "Financial Report Template",
					"template_name": "Test P&L Template",
					"report_type": "Profit and Loss Statement",
					"rows": [
						{
							"reference_code": "INC001",
							"display_name": "Income",
							"data_source": "Account Data",
							"balance_type": "Closing Balance",
							"calculation_formula": '["root_type", "=", "Income"]',
						},
						{
							"reference_code": "EXP001",
							"display_name": "Expenses",
							"data_source": "Account Data",
							"balance_type": "Closing Balance",
							"calculation_formula": '["root_type", "=", "Expense"]',
						},
					],
				}
			).insert()

		cls.test_template = frappe.get_doc("Financial Report Template", "Test P&L Template")

	@staticmethod
	def create_test_template_with_rows(rows_data):
		template_name = f"Test Template {frappe.generate_hash()[:8]}"
		return frappe.get_doc(
			{"doctype": "Financial Report Template", "template_name": template_name, "rows": rows_data}
		)

	def test_execute_uses_selected_companies_for_template_rows(self):
		company_a = self.company_a
		company_b = self.company_b

		income_a = self._get_accounts(company_a, "Income")[0]
		expense_a = self._get_accounts(company_a, "Expense")[0]
		asset_a = self._get_accounts(company_a, "Asset", exclude_account_types=["Receivable"])[0]
		liability_a = self._get_accounts(company_a, "Liability", exclude_account_types=["Payable"])[0]
		expense_b = self._get_accounts(company_b, "Expense")[0]
		liability_b = self._get_accounts(company_b, "Liability", exclude_account_types=["Payable"])[0]

		journal_entries = []
		template = None

		try:
			journal_entries.append(self._make_journal_entry(company_a, asset_a, income_a, 200, "2027-04-05"))
			journal_entries.append(
				self._make_journal_entry(company_b, expense_b, liability_b, 200, "2027-04-09")
			)
			journal_entries.append(
				self._make_journal_entry(company_a, expense_a, liability_a, 50, "2027-04-12")
			)

			template = self.create_test_template_with_rows(
				[
					{
						"reference_code": "A_INTERCO",
						"display_name": "Company A Intercompany Income",
						"data_source": "Account Data",
						"balance_type": "Period Movement (Debits - Credits)",
						"reverse_sign": 1,
						"hidden_calculation": 1,
						"calculation_formula": self._make_account_filter(company_a, income_a),
					},
					{
						"reference_code": "B_INTERCO",
						"display_name": "Company B Intercompany Expense",
						"data_source": "Account Data",
						"balance_type": "Period Movement (Debits - Credits)",
						"hidden_calculation": 1,
						"calculation_formula": self._make_account_filter(company_b, expense_b),
					},
					{
						"reference_code": "LOCAL_EXPENSE",
						"display_name": "Local Expense",
						"data_source": "Account Data",
						"balance_type": "Period Movement (Debits - Credits)",
						"calculation_formula": self._make_account_filter(company_a, expense_a),
					},
					{
						"reference_code": "NET_INTERCO",
						"display_name": "Intercompany Eliminated",
						"data_source": "Calculated Amount",
						"hide_when_empty": 1,
						"calculation_formula": "A_INTERCO - B_INTERCO",
					},
				]
			)
			template.insert()

			columns, data, _, _ = FinancialReportEngine().execute(
				frappe._dict(
					{
						"report_template": template.name,
						# Mimic the default single-company filter still being populated in the UI.
						"company": company_a,
						"companies": [company_a, company_b],
						"period_start_date": "2027-04-01",
						"period_end_date": "2027-04-30",
						"filter_based_on": "Date Range",
						"periodicity": "Monthly",
						"selected_view": "Report",
						"accumulated_values": 0,
					}
				)
			)

			period_key = self._get_period_key(columns)
			local_expense_row = next(row for row in data if row.get("account_name") == "Local Expense")

			self.assertEqual(flt(local_expense_row.get(period_key), 2), 50.0)
			self.assertFalse(any(row.get("account_name") == "Intercompany Eliminated" for row in data))
		finally:
			for journal_entry in reversed(journal_entries):
				journal_entry.cancel()

	def test_execute_rejects_multi_company_reports_with_mixed_default_currencies(self):
		with self.assertRaisesRegex(frappe.ValidationError, "same default currency"):
			FinancialReportEngine().execute(
				frappe._dict(
					{
						"report_template": self.test_template.name,
						"company": self.company_a,
						"companies": [self.company_a, self.company_c],
						"period_start_date": "2027-04-01",
						"period_end_date": "2027-04-30",
						"filter_based_on": "Date Range",
						"periodicity": "Monthly",
						"selected_view": "Report",
					}
				)
			)
