# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import whitelist_for_tests

from erpnext.accounts.doctype.financial_report_template.financial_report_validation import (
	AccountFilterValidator,
	FormulaValidator,
	get_valid_api_method,
)
from erpnext.tests.utils import ERPNextTestSuite


class FinancialReportTemplateTestCase(ERPNextTestSuite):
	"""Utility class with common setup and helper methods for all test classes"""

	def cancel_docs(self, docs):
		"""Cancel submitted docs in reverse creation order to avoid dependency issues."""
		for doc in reversed(docs):
			if doc:
				doc.reload()
				if doc.docstatus == 1:
					doc.cancel()

	def setUp(self):
		"""Set up test data"""
		self.create_test_template()

	@classmethod
	def create_test_template(cls):
		"""Create a test financial report template"""
		if not frappe.db.exists("Financial Report Template", "Test P&L Template"):
			template = frappe.get_doc(
				{
					"doctype": "Financial Report Template",
					"template_name": "Test P&L Template",
					"report_type": "Profit and Loss Statement",
					"rows": [
						{
							"reference_code": "INC001",
							"display_name": "Income",
							"indentation_level": 0,
							"data_source": "Account Data",
							"balance_type": "Closing Balance",
							"bold_text": 1,
							"calculation_formula": '["root_type", "=", "Income"]',
						},
						{
							"reference_code": "EXP001",
							"display_name": "Expenses",
							"indentation_level": 0,
							"data_source": "Account Data",
							"balance_type": "Closing Balance",
							"bold_text": 1,
							"calculation_formula": '["root_type", "=", "Expense"]',
						},
						{
							"reference_code": "NET001",
							"display_name": "Net Profit/Loss",
							"indentation_level": 0,
							"data_source": "Calculated Amount",
							"bold_text": 1,
							"calculation_formula": "INC001 - EXP001",
						},
					],
				}
			)
			template.insert()

		cls.test_template = frappe.get_doc("Financial Report Template", "Test P&L Template")

	@staticmethod
	def create_test_template_with_rows(rows_data):
		"""Helper method to create test template with specific rows"""
		template_name = f"Test Template {frappe.generate_hash()[:8]}"
		template = frappe.get_doc(
			{"doctype": "Financial Report Template", "template_name": template_name, "rows": rows_data}
		)
		return template


def not_whitelisted_method(**kwargs):
	return [42.0]


@whitelist_for_tests(methods=["POST"])
def whitelisted_post_only_method(**kwargs):
	return [42.0]


@whitelist_for_tests(methods=["GET"])
def whitelisted_get_method(**kwargs):
	return [42.0]


class TestCustomAPIValidation(FinancialReportTemplateTestCase):
	"""Custom API rows must point to whitelisted methods that permit GET"""

	TEST_MODULE = "erpnext.accounts.doctype.financial_report_template.test_financial_report_template"
	NOT_WHITELISTED = f"{TEST_MODULE}.not_whitelisted_method"
	WHITELISTED_POST_ONLY = f"{TEST_MODULE}.whitelisted_post_only_method"
	WHITELISTED_GET = f"{TEST_MODULE}.whitelisted_get_method"

	def create_api_template(self, api_path):
		template = self.create_test_template_with_rows(
			[
				{
					"reference_code": "API001",
					"display_name": "API Row",
					"data_source": "Custom API",
					"calculation_formula": api_path,
				}
			]
		)
		template.report_type = "Profit and Loss Statement"
		return template

	def test_get_valid_api_method(self):
		self.assertRaises(frappe.PermissionError, get_valid_api_method, self.NOT_WHITELISTED)
		self.assertRaises(frappe.PermissionError, get_valid_api_method, self.WHITELISTED_POST_ONLY)
		self.assertEqual(get_valid_api_method(self.WHITELISTED_GET), frappe.get_attr(self.WHITELISTED_GET))

	def test_save_rejects_invalid_api_methods(self):
		for api_path in (self.NOT_WHITELISTED, self.WHITELISTED_POST_ONLY):
			template = self.create_api_template(api_path)
			self.assertRaises(frappe.ValidationError, template.insert)

	def test_save_allows_get_whitelisted_method(self):
		template = self.create_api_template(self.WHITELISTED_GET)
		template.insert()
		template.delete()

	def test_engine_rejects_invalid_api_methods(self):
		from erpnext.accounts.doctype.financial_report_template.financial_report_engine import (
			ReportContext,
			RowProcessor,
		)

		for api_path in (self.NOT_WHITELISTED, self.WHITELISTED_POST_ONLY):
			template = self.create_api_template(api_path)
			context = ReportContext(template=template, filters={}, period_list=[{"key": "p1"}])
			processor = RowProcessor(context)
			self.assertRaises(frappe.PermissionError, processor._process_api_row, template.rows[0])

	def test_engine_calls_valid_api_method(self):
		from erpnext.accounts.doctype.financial_report_template.financial_report_engine import (
			ReportContext,
			RowProcessor,
		)

		template = self.create_api_template(self.WHITELISTED_GET)
		context = ReportContext(template=template, filters={}, period_list=[{"key": "p1"}])
		processor = RowProcessor(context)
		row_data = processor._process_api_row(template.rows[0])
		self.assertEqual(row_data.values, [42.0])

	def test_validation_keeps_message_log_clean(self):
		validator = FormulaValidator(frappe._dict(rows=[]))
		message_count = len(frappe.local.message_log)

		# last path raises AppNotInstalledError, which also logs a message via frappe.throw
		for api_path in (self.NOT_WHITELISTED, self.WHITELISTED_POST_ONLY, "missing_app.api.method"):
			row = frappe._dict(data_source="Custom API", calculation_formula=api_path, idx=1)
			result = validator.validate(row)
			self.assertFalse(result.is_valid)
			self.assertEqual(len(frappe.local.message_log), message_count)


class TestAccountFilter(FinancialReportTemplateTestCase):
	"""Filter fields must be validated on the account-filter parser path."""

	@staticmethod
	def _row(formula, **extra):
		return frappe._dict(calculation_formula=formula, idx=1, **extra)

	def test_validate_filter_enforces_allow_list_without_data_source(self):
		# the parser path has no `data_source`; the field allow-list must still apply
		validator = AccountFilterValidator()
		self.assertFalse(validator.validate_filter(self._row('["bad_field", "=", "x"]')).is_valid)
		self.assertTrue(validator.validate_filter(self._row('["root_type", "=", "Income"]')).is_valid)

	def test_validate_gate_still_opts_out_for_non_account_data(self):
		# validate() is the dispatch gate: it must not validate non "Account Data" rows
		validator = AccountFilterValidator()
		row = self._row('["bad_field", "=", "x"]', data_source="Custom API")
		self.assertTrue(validator.validate(row).is_valid)

	def test_error_message_labels_and_escapes_field(self):
		validator = AccountFilterValidator()
		result = validator.validate_filter(self._row('["<script>", "=", "x"]'))
		message = str(result.issues[0])
		self.assertIn("[Account Filter]", message)
		self.assertIn("&lt;script&gt;", message)
		self.assertNotIn("<script>", message)

	def test_build_conditions_raises_on_invalid_field_when_opted_in(self):
		from erpnext.accounts.doctype.financial_report_template.financial_report_engine import (
			FilterExpressionParser,
		)

		account = frappe.qb.DocType("Account")
		rows = [self._row('["bad_field", "=", "x"]')]
		parser = FilterExpressionParser()

		# default: invalid rows are skipped, not raised
		self.assertIsNone(parser.build_conditions(rows, account))

		# opted in (the get_filtered_accounts path): invalid rows raise
		self.assertRaises(
			frappe.ValidationError, parser.build_conditions, rows, account, raise_on_invalid=True
		)

	def test_build_conditions_empty_returns_none(self):
		from erpnext.accounts.doctype.financial_report_template.financial_report_engine import (
			FilterExpressionParser,
		)

		account = frappe.qb.DocType("Account")
		self.assertIsNone(FilterExpressionParser().build_conditions([], account))

	def test_endpoint_requires_company(self):
		from erpnext.accounts.doctype.financial_report_template.financial_report_engine import (
			get_filtered_accounts,
		)

		self.assertRaises(frappe.ValidationError, get_filtered_accounts, "", "[]")

	def test_endpoint_rejects_invalid_field(self):
		from erpnext.accounts.doctype.financial_report_template.financial_report_engine import (
			get_filtered_accounts,
		)

		company = frappe.get_all("Company", limit=1, pluck="name")[0]
		rows = frappe.as_json([{"calculation_formula": '["bad_field", "=", "x"]'}])
		self.assertRaises(frappe.ValidationError, get_filtered_accounts, company, rows)

	def test_endpoint_empty_rows_returns_all_company_accounts(self):
		# filters are optional: no filter returns every enabled, non-group account of the company
		from erpnext.accounts.doctype.financial_report_template.financial_report_engine import (
			get_filtered_accounts,
		)

		company = frappe.get_all("Company", limit=1, pluck="name")[0]
		expected = frappe.get_all(
			"Account",
			filters={"company": company, "disabled": 0, "is_group": 0},
			pluck="name",
		)
		self.assertEqual(sorted(get_filtered_accounts(company, "[]")), sorted(expected))
