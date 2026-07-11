# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import flt

from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.report.custom_financial_statement.custom_financial_statement import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestCustomFinancialStatement(ERPNextTestSuite):
	"""The report renders a Financial Report Template through FinancialReportEngine.
	These tests exercise its own entry point: a template with an account-data row
	and a calculated row, and the guard that returns nothing without a template."""

	def setUp(self):
		frappe.set_user("Administrator")
		self.company = "_Test Company"
		self.expense_account = "_Test Account Cost for Goods Sold - _TC"
		self.cash_account = "Cash - _TC"

	def _make_template(self):
		# rows filter by exact account name so the value is isolated from other data
		template_name = f"Test Custom FS {frappe.generate_hash()[:8]}"
		return frappe.get_doc(
			{
				"doctype": "Financial Report Template",
				"template_name": template_name,
				"report_type": "Profit and Loss Statement",
				"rows": [
					{
						"reference_code": "EXP",
						"display_name": "Test Expense",
						"indentation_level": 0,
						"data_source": "Account Data",
						"balance_type": "Closing Balance",
						"calculation_formula": f'["name", "=", "{self.expense_account}"]',
					},
					{
						"reference_code": "EXP_X2",
						"display_name": "Expense Doubled",
						"indentation_level": 0,
						"data_source": "Calculated Amount",
						"calculation_formula": "EXP * 2",
					},
				],
			}
		).insert()

	def _filters(self, template_name):
		return frappe._dict(
			{
				"company": self.company,
				"report_template": template_name,
				"from_fiscal_year": "2024",
				"to_fiscal_year": "2024",
				"period_start_date": "2024-01-01",
				"period_end_date": "2024-12-31",
				"filter_based_on": "Date Range",
				"periodicity": "Yearly",
				"accumulated_values": 0,
			}
		)

	def test_account_and_calculated_rows(self):
		make_journal_entry(
			self.expense_account,
			self.cash_account,
			2000,
			posting_date="2024-06-15",
			company=self.company,
			submit=True,
		)
		template = self._make_template()

		columns, data = execute(self._filters(template.template_name))[:2]
		self.assertTrue(columns)

		rows = {row.get("account_name"): row for row in data}
		self.assertIn("Test Expense", rows)
		self.assertIn("Expense Doubled", rows)

		period_keys = rows["Test Expense"].get("_segment_info", {}).get("period_keys", [])
		self.assertTrue(period_keys, "expected at least one period key in _segment_info")
		period_key = period_keys[0]

		# the account-data row picks up the posted expense; the calculated row doubles it
		self.assertEqual(flt(rows["Test Expense"][period_key]), 2000.0)
		self.assertEqual(flt(rows["Expense Doubled"][period_key]), 4000.0)

	def test_no_template_returns_nothing(self):
		"""Without a report_template the report short-circuits and returns None."""
		self.assertIsNone(execute(frappe._dict({"company": self.company})))
