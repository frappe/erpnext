# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from typing import Any, ClassVar

import frappe
from frappe.tests.classes.context_managers import patch_hooks
from frappe.tests.utils import whitelist_for_tests

from erpnext.accounts.doctype.financial_report_template.financial_report_validation import (
	API_METHODS_HOOK,
	FORMULA_FUNCTIONS,
	AccountFilterValidator,
	CalculationFormulaValidator,
	FormulaValidator,
	TemplateStructureValidator,
	extract_reference_codes_from_formula,
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


# calls to the recording methods below, so tests can tell if a method ran
CALLBACK_CALLS = []


@whitelist_for_tests(methods=["GET"])
def recording_get_method(filters: dict, periods: list, row: Any):
	CALLBACK_CALLS.append(
		frappe._dict(method="recording", user=frappe.session.user, filters=filters, periods=periods, row=row)
	)
	return [10.0 * (i + 1) for i in range(len(periods))]


@whitelist_for_tests(methods=["GET"])
def other_recording_get_method(periods: list, **kwargs):
	CALLBACK_CALLS.append(frappe._dict(method="other", user=frappe.session.user))
	return [1.0] * len(periods)


@whitelist_for_tests(methods=["GET"])
def restricted_get_method(periods: list, **kwargs):
	CALLBACK_CALLS.append(frappe._dict(method="restricted", user=frappe.session.user))
	frappe.has_permission("Error Log", "read", throw=True)
	return [99.0] * len(periods)


class TestCustomAPIValidation(FinancialReportTemplateTestCase):
	"""Custom API rows must point to registered, whitelisted methods that permit GET"""

	TEST_MODULE = "erpnext.accounts.doctype.financial_report_template.test_financial_report_template"
	NOT_WHITELISTED = f"{TEST_MODULE}.not_whitelisted_method"
	WHITELISTED_POST_ONLY = f"{TEST_MODULE}.whitelisted_post_only_method"
	WHITELISTED_GET = f"{TEST_MODULE}.whitelisted_get_method"
	RECORDING = f"{TEST_MODULE}.recording_get_method"
	OTHER_RECORDING = f"{TEST_MODULE}.other_recording_get_method"
	RESTRICTED = f"{TEST_MODULE}.restricted_get_method"
	MISSING_APP = "missing_app.api.method"

	TEMPLATE_AUTHOR = "fr-template-author@example.com"
	REPORT_RUNNER = "fr-template-runner@example.com"

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.make_test_user(cls.TEMPLATE_AUTHOR, ["Accounts Manager"])
		cls.make_test_user(cls.REPORT_RUNNER, ["System Manager", "Accounts Manager"])

	def setUp(self):
		super().setUp()
		CALLBACK_CALLS.clear()

	@staticmethod
	def make_test_user(email, roles):
		if frappe.db.exists("User", email):
			user = frappe.get_doc("User", email)
		else:
			user = frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": email.split("@")[0],
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)

		user.add_roles(*roles)

	def register(self, *api_paths):
		return patch_hooks({API_METHODS_HOOK: list(api_paths)})

	def create_api_template(self, *api_paths, extra_rows=None):
		rows = [
			{
				"reference_code": f"API00{idx}",
				"display_name": f"API Row {idx}",
				"data_source": "Custom API",
				"calculation_formula": api_path,
			}
			for idx, api_path in enumerate(api_paths, start=1)
		]
		template = self.create_test_template_with_rows(rows + (extra_rows or []))
		template.report_type = "Profit and Loss Statement"
		return template

	def insert_legacy_template(self, *api_paths):
		"""
		Insert a template as it could be saved before Custom API methods needed registration.

		Validation is skipped only to store the old data. The report run under test is unchanged.
		"""
		with self.set_user(self.TEMPLATE_AUTHOR):
			template = self.create_api_template(*api_paths)
			template.flags.ignore_validate = True
			template.insert()

		return template

	def get_report_filters(self, template_name):
		return frappe._dict(
			company="_Test Company",
			filter_based_on="Date Range",
			period_start_date="2025-01-01",
			period_end_date="2026-12-31",
			periodicity="Yearly",
			report_template=template_name,
		)

	def get_report_runners(self):
		from erpnext.accounts.report.balance_sheet.balance_sheet import execute as balance_sheet
		from erpnext.accounts.report.cash_flow.cash_flow import execute as cash_flow
		from erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement import (
			execute as profit_and_loss,
		)

		return {"Balance Sheet": balance_sheet, "Profit and Loss": profit_and_loss, "Cash Flow": cash_flow}

	def assert_report_rejected(self, template_name, user=None):
		for report, execute in self.get_report_runners().items():
			with self.subTest(report=report), self.set_user(user or self.REPORT_RUNNER):
				self.assertRaises(frappe.PermissionError, execute, self.get_report_filters(template_name))

		self.assertEqual(CALLBACK_CALLS, [])

	@staticmethod
	def get_row_values(result, display_name):
		row = next(row for row in result[1] if row.get("account_name") == display_name)
		return [row[key] for key in ("dec_2025", "dec_2026")]

	def test_get_valid_api_method(self):
		with self.register(self.NOT_WHITELISTED, self.WHITELISTED_POST_ONLY, self.WHITELISTED_GET):
			self.assertRaises(frappe.PermissionError, get_valid_api_method, self.NOT_WHITELISTED)
			self.assertRaises(frappe.PermissionError, get_valid_api_method, self.WHITELISTED_POST_ONLY)
			self.assertEqual(
				get_valid_api_method(self.WHITELISTED_GET), frappe.get_attr(self.WHITELISTED_GET)
			)

	def test_unregistered_get_method_is_rejected(self):
		# whitelisted and permits GET, but no app registered it
		self.assertNotIn(self.WHITELISTED_GET, frappe.get_hooks(API_METHODS_HOOK))
		self.assertRaises(frappe.PermissionError, get_valid_api_method, self.WHITELISTED_GET)

		with self.register():
			self.assertRaises(frappe.PermissionError, get_valid_api_method, self.WHITELISTED_GET)

	def test_registration_is_checked_before_import(self):
		# an unregistered path is refused before the app check that importing does
		self.assertRaises(frappe.PermissionError, get_valid_api_method, self.MISSING_APP)

		# a registered path of an app that is not installed is still refused on import
		with self.register(self.MISSING_APP):
			self.assertRaises(frappe.AppNotInstalledError, get_valid_api_method, self.MISSING_APP)

	def test_registration_needs_exact_path(self):
		with self.register(self.WHITELISTED_GET, self.TEST_MODULE):
			for api_path in (
				self.RECORDING,  # same module as a registered method
				f"{self.WHITELISTED_GET}.__call__",
				f" {self.WHITELISTED_GET}",
				self.WHITELISTED_GET.upper(),
			):
				with self.subTest(api_path=api_path):
					self.assertRaises(frappe.PermissionError, get_valid_api_method, api_path)

	def test_malformed_paths_are_rejected(self):
		with self.register(self.WHITELISTED_GET):
			for api_path in (None, "", 42, [self.WHITELISTED_GET], (self.WHITELISTED_GET,)):
				with self.subTest(api_path=api_path):
					self.assertRaises(frappe.PermissionError, get_valid_api_method, api_path)

	def test_request_cannot_register_method(self):
		frappe.local.form_dict[API_METHODS_HOOK] = [self.WHITELISTED_GET]
		frappe.flags[API_METHODS_HOOK] = [self.WHITELISTED_GET]
		self.addCleanup(frappe.local.form_dict.pop, API_METHODS_HOOK, None)
		self.addCleanup(frappe.flags.pop, API_METHODS_HOOK, None)

		self.assertRaises(frappe.PermissionError, get_valid_api_method, self.WHITELISTED_GET)

	def test_registration_is_read_on_each_check(self):
		with self.register(self.WHITELISTED_GET):
			self.assertTrue(get_valid_api_method(self.WHITELISTED_GET))

		self.assertRaises(frappe.PermissionError, get_valid_api_method, self.WHITELISTED_GET)

	def test_save_rejects_invalid_api_methods(self):
		with self.register(self.NOT_WHITELISTED, self.WHITELISTED_POST_ONLY):
			for api_path in (self.NOT_WHITELISTED, self.WHITELISTED_POST_ONLY, self.WHITELISTED_GET):
				with self.subTest(api_path=api_path), self.set_user(self.TEMPLATE_AUTHOR):
					template = self.create_api_template(api_path)
					self.assertRaises(frappe.ValidationError, template.insert)

	def test_save_allows_registered_get_method(self):
		with self.register(self.WHITELISTED_GET), self.set_user(self.TEMPLATE_AUTHOR):
			template = self.create_api_template(self.WHITELISTED_GET)
			template.insert()
			template.delete()

	def test_edit_cannot_add_unregistered_method(self):
		with self.set_user(self.TEMPLATE_AUTHOR):
			template = self.create_test_template_with_rows(
				[
					{
						"reference_code": "INC001",
						"display_name": "Income",
						"data_source": "Account Data",
						"balance_type": "Closing Balance",
						"calculation_formula": '["root_type", "=", "Income"]',
					}
				]
			)
			template.report_type = "Profit and Loss Statement"
			template.insert()

			row = template.rows[0]
			row.data_source = "Custom API"
			row.calculation_formula = self.WHITELISTED_GET
			self.assertRaises(frappe.ValidationError, template.save)

	def test_engine_rejects_invalid_api_methods(self):
		from erpnext.accounts.doctype.financial_report_template.financial_report_engine import (
			ReportContext,
			RowProcessor,
		)

		with self.register(self.NOT_WHITELISTED, self.WHITELISTED_POST_ONLY):
			for api_path in (self.NOT_WHITELISTED, self.WHITELISTED_POST_ONLY, self.WHITELISTED_GET):
				template = self.create_api_template(api_path)
				context = ReportContext(template=template, filters={}, period_list=[{"key": "p1"}])
				processor = RowProcessor(context)
				self.assertRaises(frappe.PermissionError, processor._process_api_row, template.rows[0])

	def test_engine_calls_valid_api_method(self):
		from erpnext.accounts.doctype.financial_report_template.financial_report_engine import (
			ReportContext,
			RowProcessor,
		)

		with self.register(self.WHITELISTED_GET):
			template = self.create_api_template(self.WHITELISTED_GET)
			context = ReportContext(template=template, filters={}, period_list=[{"key": "p1"}])
			processor = RowProcessor(context)
			row_data = processor._process_api_row(template.rows[0])

		self.assertEqual(row_data.values, [42.0])

	def test_report_rejects_legacy_unregistered_method(self):
		# the template author cannot save this path today, but older templates may contain it
		template = self.insert_legacy_template(self.RECORDING)

		self.assert_report_rejected(template.name)
		self.assertIn(self.RECORDING, str(frappe.local.message_log[-1]))
		self.assertIn("Template row 1", str(frappe.local.message_log[-1]))

	def test_report_rejects_method_after_registration_is_removed(self):
		with self.register(self.RECORDING), self.set_user(self.TEMPLATE_AUTHOR):
			template = self.create_api_template(self.RECORDING).insert()

		self.assert_report_rejected(template.name)

	def test_report_checks_all_api_rows_before_calling_any(self):
		with self.register(self.RECORDING), self.set_user(self.TEMPLATE_AUTHOR):
			template = self.create_api_template(self.RECORDING).insert()

		# a later edit adds a row that is not registered
		template.append(
			"rows",
			{
				"reference_code": "API002",
				"display_name": "API Row 2",
				"data_source": "Custom API",
				"calculation_formula": self.OTHER_RECORDING,
			},
		)
		template.flags.ignore_validate = True
		template.save()

		with self.register(self.RECORDING):
			self.assert_report_rejected(template.name)

	def test_report_runs_registered_method(self):
		with self.register(self.RECORDING), self.set_user(self.TEMPLATE_AUTHOR):
			template = self.create_api_template(
				self.RECORDING,
				extra_rows=[
					{
						"reference_code": "CALC001",
						"display_name": "Doubled",
						"data_source": "Calculated Amount",
						"calculation_formula": "API001 * 2",
					}
				],
			).insert()

		for report, execute in self.get_report_runners().items():
			CALLBACK_CALLS.clear()
			with self.subTest(report=report), self.register(self.RECORDING), self.set_user(
				self.REPORT_RUNNER
			):
				filters = self.get_report_filters(template.name)
				result = execute(filters)

				self.assertEqual(len(CALLBACK_CALLS), 1)
				call = CALLBACK_CALLS[0]
				self.assertEqual(call.user, self.REPORT_RUNNER)
				self.assertEqual(call.filters, filters)
				self.assertEqual([period["key"] for period in call.periods], ["dec_2025", "dec_2026"])
				self.assertEqual(call.row.reference_code, "API001")

				self.assertEqual(self.get_row_values(result, "API Row 1"), [10.0, 20.0])
				self.assertEqual(self.get_row_values(result, "Doubled"), [20.0, 40.0])

	def test_registered_method_runs_with_runner_permissions(self):
		with self.register(self.RESTRICTED), self.set_user(self.TEMPLATE_AUTHOR):
			template = self.create_api_template(self.RESTRICTED).insert()

		from erpnext.accounts.report.balance_sheet.balance_sheet import execute

		filters = self.get_report_filters(template.name)

		# the method refuses a runner without access, so its data is not shown
		with self.register(self.RESTRICTED), self.set_user(self.TEMPLATE_AUTHOR):
			result = execute(filters)

		self.assertEqual([call.user for call in CALLBACK_CALLS], [self.TEMPLATE_AUTHOR])
		self.assertEqual(self.get_row_values(result, "API Row 1"), [0.0, 0.0])

		with self.register(self.RESTRICTED), self.set_user(self.REPORT_RUNNER):
			result = execute(filters)

		self.assertEqual(self.get_row_values(result, "API Row 1"), [99.0, 99.0])

	def test_report_without_api_rows_needs_no_registration(self):
		from erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement import execute

		with self.register(), self.set_user(self.REPORT_RUNNER):
			result = execute(self.get_report_filters(self.test_template.name))

		self.assertTrue(result[1])

	def test_validation_keeps_message_log_clean(self):
		validator = FormulaValidator(frappe._dict(rows=[]))
		message_count = len(frappe.local.message_log)

		# unregistered paths are refused by frappe.throw, which also logs a message
		for api_path in (self.NOT_WHITELISTED, self.WHITELISTED_POST_ONLY, self.MISSING_APP):
			row = frappe._dict(data_source="Custom API", calculation_formula=api_path, idx=1)
			result = validator.validate(row)
			self.assertFalse(result.is_valid)
			self.assertEqual(len(frappe.local.message_log), message_count)

		# registered paths are refused later, by the whitelist, GET and app checks
		with self.register(self.NOT_WHITELISTED, self.WHITELISTED_POST_ONLY, self.MISSING_APP):
			for api_path in (self.NOT_WHITELISTED, self.WHITELISTED_POST_ONLY, self.MISSING_APP):
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
		self.assertIn("[Account Filter]", str(result.issues[0]))

		# escaping happens where the message is rendered, not where it is built
		frappe.clear_messages()
		with self.assertRaises(frappe.ValidationError):
			result.notify_user()
		message = frappe.get_message_log()[-1]["message"]
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


class TestFormulaEnvironment(FinancialReportTemplateTestCase):
	"""Validator and engine must evaluate a formula in the same environment."""

	@staticmethod
	def _calc(row_data):
		from erpnext.accounts.doctype.financial_report_template.financial_report_engine import (
			FormulaCalculator,
		)

		return FormulaCalculator(row_data, [{"key": "p1"}])

	@staticmethod
	def _row(formula):
		return frappe._dict(
			calculation_formula=formula,
			idx=1,
			reverse_sign=0,
			data_source="Calculated Amount",
			reference_code="X",
		)

	def test_engine_keeps_reference_codes_named_like_builtins(self):
		# "int" and "long" are whitelisted safe_eval globals; the row values must win
		calc = self._calc({"int": [500.0], "long": [2000.0]})
		self.assertEqual(calc.evaluate_formula(self._row("int + long"))[0], 2500.0)

	def test_validator_keeps_reference_codes_named_like_builtins(self):
		validator = CalculationFormulaValidator({"int", "long"})
		self.assertTrue(validator.validate(self._row("int + long")).is_valid)

	def test_engine_uses_the_shared_function_list(self):
		context = self._calc({"A": [1.0]})._build_context(0)
		for name, function in FORMULA_FUNCTIONS.items():
			self.assertIs(context[name], function)

	def test_rounding_matches_math_module(self):
		calc = self._calc({"A": [1.0]})
		self.assertEqual(calc.evaluate_formula(self._row("floor(-2.5)"))[0], -3.0)
		self.assertEqual(calc.evaluate_formula(self._row("ceil(-2.5)"))[0], -2.0)


class TestCalculationFormula(FinancialReportTemplateTestCase):
	"""A formula is read before a template can be saved."""

	@staticmethod
	def _validate(formula, codes=("A", "B", "C")):
		row = frappe._dict(
			calculation_formula=formula, idx=1, data_source="Calculated Amount", reference_code="X"
		)
		return CalculationFormulaValidator(set(codes)).validate(row)

	def test_broken_syntax_is_rejected(self):
		self.assertFalse(self._validate("A +").is_valid)
		self.assertFalse(self._validate("(A - B").is_valid)

	def test_constructs_safe_eval_rejects_are_caught_on_save(self):
		self.assertFalse(self._validate("(y := A)").is_valid)

	def test_unknown_names_are_rejected_on_save(self):
		self.assertFalse(self._validate("A + NOPE").is_valid)
		self.assertFalse(self._validate("nosuchfn(A)").is_valid)

	def test_divisors_are_left_to_the_engine(self):
		# whether a divisor is zero depends on the data, so the engine decides
		self.assertTrue(self._validate("A / B").is_valid)
		self.assertTrue(self._validate("A / (B - C)").is_valid)
		self.assertTrue(self._validate("(A - B) / (A - C)").is_valid)
		self.assertTrue(self._validate("A / (0 + 1)").is_valid)
		self.assertTrue(self._validate("ROM / (CAS + FDE - ROM)", ("ROM", "CAS", "FDE")).is_valid)

	def test_conditional_formulas_are_allowed(self):
		# shipped templates use this shape for every ratio line
		self.assertTrue(self._validate("A / B if B != 0 else 0").is_valid)
		self.assertTrue(self._validate("A if A > B else B").is_valid)

	def test_self_reference_is_an_error(self):
		row = frappe._dict(
			calculation_formula="X + 1", idx=1, data_source="Calculated Amount", reference_code="X"
		)
		self.assertFalse(CalculationFormulaValidator({"A", "X"}).validate(row).is_valid)


class TestFilterOperatorCase(FinancialReportTemplateTestCase):
	"""Operators are matched case-insensitively, so their value checks must be too."""

	@staticmethod
	def _row(formula):
		return frappe._dict(calculation_formula=formula, idx=1)

	def test_uppercase_in_requires_a_list_value(self):
		validator = AccountFilterValidator()
		self.assertFalse(validator.validate_filter(self._row('["root_type", "IN", "Income"]')).is_valid)
		self.assertFalse(validator.validate_filter(self._row('["root_type", "NOT IN", "Income"]')).is_valid)

	def test_uppercase_in_accepts_a_list_value(self):
		validator = AccountFilterValidator()
		self.assertTrue(validator.validate_filter(self._row('["root_type", "IN", ["Income"]]')).is_valid)


class TestLineReferenceNames(FinancialReportTemplateTestCase):
	"""A line reference becomes a name in formulas, so it must be usable as one."""

	@staticmethod
	def _validate(code):
		template = frappe._dict(rows=[frappe._dict(reference_code=code, idx=1, data_source="Blank Line")])
		return TemplateStructureValidator()._validate_reference_codes(template)

	def test_plain_codes_are_accepted(self):
		for code in ("REV", "CA100", "cash_flow_2"):
			self.assertTrue(self._validate(code).is_valid, code)

	def test_hyphen_is_rejected(self):
		# "-" reads as subtraction in a formula and is not a valid Python name
		self.assertFalse(self._validate("REV-COGS").is_valid)

	def test_python_keyword_is_rejected(self):
		for code in ("if", "None", "class"):
			self.assertFalse(self._validate(code).is_valid, code)

	def test_formula_function_name_is_rejected(self):
		# these would be overwritten by the function of the same name
		for code in ("sum", "round", "abs"):
			self.assertFalse(self._validate(code).is_valid, code)

	def test_surrounding_spaces_are_normalised_before_validation(self):
		template = frappe.new_doc("Financial Report Template")
		template.template_name = "Spaces"
		template.append("rows", {"reference_code": "  REV  ", "data_source": "Blank Line"})
		template.append(
			"rows",
			{
				"reference_code": "X",
				"data_source": "Calculated Amount",
				"calculation_formula": "  REV * 2  ",
			},
		)
		template.before_validate()
		self.assertEqual(template.rows[0].reference_code, "REV")
		self.assertEqual(template.rows[1].calculation_formula, "REV * 2")

	def test_validation_does_not_modify_the_row(self):
		row = frappe._dict(
			calculation_formula="  REV * 2  ",
			idx=1,
			data_source="Calculated Amount",
			reference_code="X",
		)
		CalculationFormulaValidator({"REV", "X"}).validate(row)
		self.assertEqual(row.calculation_formula, "  REV * 2  ")

	def test_invalid_reference_code_is_escaped(self):
		# this message fires when the code fails the format check, so it can hold anything
		template = frappe._dict(rows=[frappe._dict(reference_code="<img src=x onerror=alert(1)>", idx=1)])
		result = TemplateStructureValidator()._validate_reference_codes(template)

		frappe.clear_messages()
		with self.assertRaises(frappe.ValidationError):
			result.notify_user()
		message = frappe.get_message_log()[-1]["message"]
		self.assertIn("&lt;img", message)
		self.assertNotIn("<img", message)


class TestReferenceCodeExtraction(FinancialReportTemplateTestCase):
	"""Dependency ordering relies on knowing which codes a formula reads."""

	CODES: ClassVar[set[str]] = {"REV", "COGS", "sum"}

	def _extract(self, formula):
		return extract_reference_codes_from_formula(formula, self.CODES)

	def test_codes_the_formula_reads(self):
		self.assertEqual(self._extract("REV - COGS"), ["COGS", "REV"])
		self.assertEqual(self._extract("round(REV, 2)"), ["REV"])

	def test_a_called_name_is_not_a_dependency(self):
		# "sum" is also a reference code here, but it is being called, not read
		self.assertEqual(self._extract("sum([REV])"), ["REV"])

	def test_a_name_the_formula_creates_is_not_a_dependency(self):
		self.assertEqual(self._extract("[REV for REV in [1]]"), [])

	def test_unparseable_formula_has_no_dependencies(self):
		self.assertEqual(self._extract("REV +"), [])

	def test_empty_formula(self):
		self.assertEqual(self._extract(""), [])
		self.assertEqual(self._extract(None), [])

	def test_result_is_sorted_so_it_is_stable(self):
		self.assertEqual(self._extract("COGS + REV"), ["COGS", "REV"])
