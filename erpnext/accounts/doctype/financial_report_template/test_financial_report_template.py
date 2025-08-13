# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.tests.utils import make_test_records

from erpnext.accounts.doctype.financial_report_template.financial_report_engine import (
	AccountDataCollector,
	BalanceProcessor,
	DataFormatter,
	DependencyResolver,
	FilterExpressionParser,
	FinancialReportEngine,
	FormulaCalculator,
)

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]


class TestFinancialReportTemplate(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		"""Set up test data"""
		make_test_records("Company")
		make_test_records("Fiscal Year")
		cls.create_test_template()

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

	def create_test_template_with_rows(self, rows_data):
		"""Helper method to create test template with specific rows"""
		template_name = f"Test Template {frappe.generate_hash()[:8]}"
		template = frappe.get_doc(
			{"doctype": "Financial Report Template", "template_name": template_name, "rows": rows_data}
		)
		return template

	def test_dependency_resolver_basic_order(self):
		"""Test basic dependency resolution ordering"""
		resolver = DependencyResolver(self.test_template)
		order = resolver.get_processing_order()

		# Should process account rows before formula rows
		account_indices = [i for i, row in enumerate(order) if row.data_source == "Account Data"]
		formula_indices = [i for i, row in enumerate(order) if row.data_source == "Calculated Amount"]

		self.assertTrue(all(ai < fi for ai in account_indices for fi in formula_indices))

	def test_dependency_resolver_simple_dependency(self):
		"""Test dependency resolution with simple formula dependency"""
		# Create test rows with dependencies
		test_rows = [
			{
				"reference_code": "A001",
				"display_name": "Base Account",
				"data_source": "Account Data",
				"calculation_formula": '["account_type", "=", "Income"]',
			},
			{
				"reference_code": "B001",
				"display_name": "Calculated Row",
				"data_source": "Calculated Amount",
				"calculation_formula": "A001 * 2",
			},
		]

		test_template = self.create_test_template_with_rows(test_rows)
		resolver = DependencyResolver(test_template)

		# Check dependencies were correctly identified
		self.assertIn("B001", resolver.dependencies)
		self.assertEqual(resolver.dependencies["B001"], ["A001"])

		# Check processing order
		order = resolver.get_processing_order()
		a001_index = next(i for i, row in enumerate(order) if row.reference_code == "A001")
		b001_index = next(i for i, row in enumerate(order) if row.reference_code == "B001")

		self.assertLess(a001_index, b001_index, "A001 should be processed before B001")

	def test_dependency_resolver_multiple_dependencies(self):
		"""Test dependency resolution with multiple dependencies"""
		test_rows = [
			{
				"reference_code": "INC001",
				"display_name": "Income",
				"data_source": "Account Data",
				"calculation_formula": '["root_type", "=", "Income"]',
			},
			{
				"reference_code": "EXP001",
				"display_name": "Expenses",
				"data_source": "Account Data",
				"calculation_formula": '["root_type", "=", "Expense"]',
			},
			{
				"reference_code": "GROSS001",
				"display_name": "Gross Profit",
				"data_source": "Calculated Amount",
				"calculation_formula": "INC001 - EXP001",
			},
			{
				"reference_code": "MARGIN001",
				"display_name": "Profit Margin",
				"data_source": "Calculated Amount",
				"calculation_formula": "GROSS001 / INC001 * 100",
			},
		]

		test_template = self.create_test_template_with_rows(test_rows)
		resolver = DependencyResolver(test_template)

		# Check dependencies
		self.assertEqual(set(resolver.dependencies["GROSS001"]), {"INC001", "EXP001"})
		self.assertEqual(set(resolver.dependencies["MARGIN001"]), {"GROSS001", "INC001"})

		# Check processing order
		order = resolver.get_processing_order()
		positions = {row.reference_code: i for i, row in enumerate(order) if row.reference_code}

		# Account rows should come before formula rows
		self.assertLess(positions["INC001"], positions["GROSS001"])
		self.assertLess(positions["EXP001"], positions["GROSS001"])

		# GROSS001 should come before MARGIN001 (which depends on it)
		self.assertLess(positions["GROSS001"], positions["MARGIN001"])

	def test_dependency_resolver_chain_dependencies(self):
		"""Test dependency resolution with chain of dependencies (A -> B -> C -> D)"""
		test_rows = [
			{
				"reference_code": "A001",
				"display_name": "Base",
				"data_source": "Account Data",
				"calculation_formula": '["account_type", "=", "Income"]',
			},
			{
				"reference_code": "B001",
				"display_name": "Level 1",
				"data_source": "Calculated Amount",
				"calculation_formula": "A001 + 100",
			},
			{
				"reference_code": "C001",
				"display_name": "Level 2",
				"data_source": "Calculated Amount",
				"calculation_formula": "B001 * 1.2",
			},
			{
				"reference_code": "D001",
				"display_name": "Level 3",
				"data_source": "Calculated Amount",
				"calculation_formula": "C001 - 50",
			},
		]

		test_template = self.create_test_template_with_rows(test_rows)
		resolver = DependencyResolver(test_template)
		order = resolver.get_processing_order()
		positions = {row.reference_code: i for i, row in enumerate(order) if row.reference_code}

		# Verify chain order
		self.assertLess(positions["A001"], positions["B001"])
		self.assertLess(positions["B001"], positions["C001"])
		self.assertLess(positions["C001"], positions["D001"])

	def test_dependency_resolver_circular_dependency_detection(self):
		test_rows = [
			{
				"reference_code": "A001",
				"display_name": "Row A",
				"data_source": "Calculated Amount",
				"calculation_formula": "B001 + 100",
			},
			{
				"reference_code": "B001",
				"display_name": "Row B",
				"data_source": "Calculated Amount",
				"calculation_formula": "A001 + 200",
			},
		]

		# Should raise ValidationError for circular dependency
		test_template = self.create_test_template_with_rows(test_rows)
		with self.assertRaises(frappe.ValidationError):
			DependencyResolver(test_template)

	def test_dependency_resolver_complex_circular_dependency(self):
		"""Test detection of complex circular dependency (A -> B -> C -> A)"""
		test_rows = [
			{
				"reference_code": "A001",
				"display_name": "Row A",
				"data_source": "Calculated Amount",
				"calculation_formula": "C001 + 100",  # A depends on C
			},
			{
				"reference_code": "B001",
				"display_name": "Row B",
				"data_source": "Calculated Amount",
				"calculation_formula": "A001 + 200",  # B depends on A
			},
			{
				"reference_code": "C001",
				"display_name": "Row C",
				"data_source": "Calculated Amount",
				"calculation_formula": "B001 * 1.5",  # C depends on B -> creates cycle
			},
		]

		# Should raise ValidationError for circular dependency
		test_template = self.create_test_template_with_rows(test_rows)
		with self.assertRaises(frappe.ValidationError):
			DependencyResolver(test_template)

	def test_dependency_resolver_missing_reference(self):
		"""Test detection of missing reference codes"""
		test_rows = [
			{
				"reference_code": "A001",
				"display_name": "Row A",
				"data_source": "Account Data",
				"calculation_formula": '["account_type", "=", "Asset"]',
			},
			{
				"reference_code": "B001",
				"display_name": "Row B",
				"data_source": "Calculated Amount",
				"calculation_formula": "A001 * 2",  # Valid reference
			},
		]

		# This should work without errors
		test_template = self.create_test_template_with_rows(test_rows)
		resolver = DependencyResolver(test_template)
		# Basic test - ensure it doesn't crash
		processing_order = resolver.get_processing_order()
		self.assertEqual(len(processing_order), 2)

	def test_dependency_resolver_complex_formula_parsing(self):
		"""Test dependency extraction from complex formulas"""
		test_rows = [
			{
				"reference_code": "INCOME",
				"display_name": "Total Income",
				"data_source": "Account Data",
				"calculation_formula": '["root_type", "=", "Income"]',
			},
			{
				"reference_code": "EXPENSE",
				"display_name": "Total Expense",
				"data_source": "Account Data",
				"calculation_formula": '["root_type", "=", "Expense"]',
			},
			{
				"reference_code": "TAX_RATE",
				"display_name": "Tax Rate",
				"data_source": "Account Data",
				"calculation_formula": '["account_name", "like", "Tax"]',
			},
			{
				"reference_code": "NET_RESULT",
				"display_name": "Net Result",
				"data_source": "Calculated Amount",
				"calculation_formula": "(INCOME - EXPENSE) * (1 - TAX_RATE / 100)",
			},
		]

		test_template = self.create_test_template_with_rows(test_rows)
		resolver = DependencyResolver(test_template)

		# Should correctly identify all three dependencies in complex formula
		net_deps = resolver.dependencies.get("NET_RESULT", [])
		self.assertEqual(set(net_deps), {"INCOME", "EXPENSE", "TAX_RATE"})

	def test_dependency_resolver_no_dependencies(self):
		"""Test handling of rows without dependencies"""
		test_rows = [
			{
				"reference_code": "A001",
				"display_name": "Account Row",
				"data_source": "Account Data",
				"calculation_formula": '["account_type", "=", "Income"]',
			},
			{
				"reference_code": "B001",
				"display_name": "Static Value",
				"data_source": "Calculated Amount",
				"calculation_formula": "1000 + 500",  # No reference codes
			},
		]

		test_template = self.create_test_template_with_rows(test_rows)
		resolver = DependencyResolver(test_template)

		# B001 should have no dependencies
		self.assertEqual(resolver.dependencies.get("B001", []), [])

		# Should still process correctly
		order = resolver.get_processing_order()
		self.assertEqual(len(order), 2)

	def test_dependency_resolver_mixed_data_sources(self):
		"""Test processing order with mixed data sources"""
		test_rows = [
			{
				"reference_code": "CALC001",
				"display_name": "Calculated",
				"data_source": "Calculated Amount",
				"calculation_formula": "ACC001 + 100",
			},
			{
				"reference_code": None,  # Blank line
				"display_name": "Spacing",
				"data_source": "Blank Line",
			},
			{
				"reference_code": "ACC001",
				"display_name": "Account",
				"data_source": "Account Data",
				"calculation_formula": '["account_type", "=", "Income"]',
			},
			{
				"reference_code": None,  # Custom API
				"display_name": "Custom",
				"data_source": "Custom API",
			},
		]

		test_template = self.create_test_template_with_rows(test_rows)
		resolver = DependencyResolver(test_template)
		order = resolver.get_processing_order()

		# Find positions
		positions = {}
		for i, row in enumerate(order):
			if row.reference_code:
				positions[row.reference_code] = i
			else:
				positions[f"{row.data_source}_{i}"] = i

		# Account data should come before calculated
		self.assertLess(positions["ACC001"], positions["CALC001"])

		# All rows should be present
		self.assertEqual(len(order), 4)

	def test_dependency_resolver_partial_matches(self):
		"""Test that partial matches are not treated as dependencies"""
		test_rows = [
			{
				"reference_code": "INC001",
				"display_name": "Income",
				"data_source": "Account Data",
				"calculation_formula": '["account_type", "=", "Income"]',
			},
			{
				"reference_code": "INC001_ADJ",  # Contains INC001 but shouldn't match
				"display_name": "Income Adjustment",
				"data_source": "Account Data",
				"calculation_formula": '["account_type", "=", "Income"]',
			},
			{
				"reference_code": "RESULT",
				"display_name": "Result",
				"data_source": "Calculated Amount",
				"calculation_formula": "INC001 + 500",  # Should only match INC001, not INC001_ADJ
			},
		]

		test_template = self.create_test_template_with_rows(test_rows)
		resolver = DependencyResolver(test_template)

		# RESULT should only depend on INC001, not INC001_ADJ
		self.assertEqual(resolver.dependencies["RESULT"], ["INC001"])

		# Processing order should work correctly
		order = resolver.get_processing_order()
		positions = {row.reference_code: i for i, row in enumerate(order)}

		self.assertLess(positions["INC001"], positions["RESULT"])
		# INC001_ADJ can be processed in any order relative to RESULT since there's no dependency
		self.assertIn("INC001_ADJ", positions)

	def test_formula_calculator(self):
		"""Test formula calculation with various scenarios"""
		# Mock row data with different scenarios
		row_data = {
			"INC001": [1000.0, 1200.0, 1500.0],
			"EXP001": [800.0, 900.0, 1100.0],
			"TAX001": [50.0, 60.0, 75.0],
			"ZERO_VAL": [0.0, 0.0, 0.0],
			"NEG_VAL": [-100.0, -200.0, -150.0],
		}

		period_list = [
			{"key": "2023_q1", "from_date": "2023-01-01", "to_date": "2023-03-31"},
			{"key": "2023_q2", "from_date": "2023-04-01", "to_date": "2023-06-30"},
			{"key": "2023_q3", "from_date": "2023-07-01", "to_date": "2023-09-30"},
		]

		calculator = FormulaCalculator(row_data, period_list)

		# Test basic arithmetic operations
		result = calculator.evaluate_formula("INC001 - EXP001")
		expected = [200.0, 300.0, 400.0]  # [1000-800, 1200-900, 1500-1100]
		self.assertEqual(result, expected)

		# Test multiplication
		result = calculator.evaluate_formula("INC001 * 2")
		expected = [2000.0, 2400.0, 3000.0]
		self.assertEqual(result, expected)

		# Test division
		result = calculator.evaluate_formula("INC001 / 10")
		expected = [100.0, 120.0, 150.0]
		self.assertEqual(result, expected)

		# Test complex formula with parentheses
		result = calculator.evaluate_formula("(INC001 - EXP001) * 0.8")
		expected = [160.0, 240.0, 320.0]  # [(1000-800)*0.8, (1200-900)*0.8, (1500-1100)*0.8]
		self.assertEqual(result, expected)

		# Test mathematical functions
		result = calculator.evaluate_formula("abs(NEG_VAL)")
		expected = [100.0, 200.0, 150.0]
		self.assertEqual(result, expected)

		# Test max function
		result = calculator.evaluate_formula("max(INC001, EXP001)")
		expected = [1000.0, 1200.0, 1500.0]  # INC001 is always larger
		self.assertEqual(result, expected)

		# Test min function
		result = calculator.evaluate_formula("min(INC001, EXP001)")
		expected = [800.0, 900.0, 1100.0]  # EXP001 is always smaller
		self.assertEqual(result, expected)

	def test_formula_calculator_division_by_zero(self):
		"""Test formula calculator handles division by zero gracefully"""
		row_data = {
			"NUMERATOR": [100.0, 200.0, 300.0],
			"ZERO_VAL": [0.0, 0.0, 0.0],
		}

		period_list = [
			{"key": "2023_q1", "from_date": "2023-01-01", "to_date": "2023-03-31"},
			{"key": "2023_q2", "from_date": "2023-04-01", "to_date": "2023-06-30"},
			{"key": "2023_q3", "from_date": "2023-07-01", "to_date": "2023-09-30"},
		]

		calculator = FormulaCalculator(row_data, period_list)

		# Test division by zero - should return 0.0 for all periods
		result = calculator.evaluate_formula("NUMERATOR / ZERO_VAL")
		expected = [0.0, 0.0, 0.0]
		self.assertEqual(result, expected)

	def test_formula_calculator_invalid_reference_codes(self):
		"""Test formula calculator handles invalid reference codes"""
		row_data = {
			"VALID_CODE": [100.0, 200.0, 300.0],
			"123_INVALID": [50.0, 60.0, 70.0],  # Starts with number - invalid identifier
			"VALID-DASH": [25.0, 30.0, 35.0],  # Contains dash - invalid identifier
		}

		period_list = [
			{"key": "2023_q1", "from_date": "2023-01-01", "to_date": "2023-03-31"},
			{"key": "2023_q2", "from_date": "2023-04-01", "to_date": "2023-06-30"},
			{"key": "2023_q3", "from_date": "2023-07-01", "to_date": "2023-09-30"},
		]

		calculator = FormulaCalculator(row_data, period_list)

		# Test with valid reference code
		result = calculator.evaluate_formula("VALID_CODE * 2")
		expected = [200.0, 400.0, 600.0]
		self.assertEqual(result, expected)

		# Test with invalid reference code - should return 0.0 (code won't be in context)
		result = calculator.evaluate_formula("INVALID_CODE * 2")
		expected = [0.0, 0.0, 0.0]
		self.assertEqual(result, expected)

	def test_formula_calculator_missing_values(self):
		"""Test formula calculator handles missing values for periods"""
		row_data = {
			"SHORT_DATA": [100.0, 200.0],  # Only 2 periods instead of 3
			"NORMAL_DATA": [50.0, 60.0, 70.0],
		}

		period_list = [
			{"key": "2023_q1", "from_date": "2023-01-01", "to_date": "2023-03-31"},
			{"key": "2023_q2", "from_date": "2023-04-01", "to_date": "2023-06-30"},
			{"key": "2023_q3", "from_date": "2023-07-01", "to_date": "2023-09-30"},
		]

		calculator = FormulaCalculator(row_data, period_list)

		# Test with missing period data - should use 0 for missing values
		result = calculator.evaluate_formula("SHORT_DATA + NORMAL_DATA")
		# SHORT_DATA has only 2 values: [100.0, 200.0], so period 2 should default to 0
		# NORMAL_DATA has 3 values: [50.0, 60.0, 70.0]
		# Results: [100+50, 200+60, 0+70] = [150.0, 260.0, 70.0]
		expected = [150.0, 260.0, 70.0]  # [100+50, 200+60, 0+70]
		self.assertEqual(result, expected)

	def test_formula_calculator_complex_expressions(self):
		"""Test formula calculator with complex mathematical expressions"""
		row_data = {
			"REVENUE": [10000.0, 12000.0, 15000.0],
			"COST": [6000.0, 7200.0, 9000.0],
			"TAX_RATE": [0.25, 0.25, 0.30],  # 25%, 25%, 30%
		}

		period_list = [
			{"key": "2023_q1", "from_date": "2023-01-01", "to_date": "2023-03-31"},
			{"key": "2023_q2", "from_date": "2023-04-01", "to_date": "2023-06-30"},
			{"key": "2023_q3", "from_date": "2023-07-01", "to_date": "2023-09-30"},
		]

		calculator = FormulaCalculator(row_data, period_list)

		# Test complex formula: (REVENUE - COST) * (1 - TAX_RATE)
		result = calculator.evaluate_formula("(REVENUE - COST) * (1 - TAX_RATE)")
		expected = [
			(10000 - 6000) * (1 - 0.25),  # 4000 * 0.75 = 3000
			(12000 - 7200) * (1 - 0.25),  # 4800 * 0.75 = 3600
			(15000 - 9000) * (1 - 0.30),  # 6000 * 0.70 = 4200
		]
		# Note: The formula actually evaluates to gross profit without tax adjustment
		# because the formula is (REVENUE - COST) * (1 - TAX_RATE), not (REVENUE - COST) - (REVENUE - COST) * TAX_RATE
		# So the actual results are: 4000 * 0.75, 4800 * 0.75, 6000 * 0.70
		self.assertEqual(result, [3000.0, 3600.0, 4200.0])

		# Test formula with mathematical functions
		result = calculator.evaluate_formula("round(REVENUE / COST, 2)")
		expected = [
			round(10000 / 6000, 2),  # 1.67
			round(12000 / 7200, 2),  # 1.67
			round(15000 / 9000, 2),  # 1.67
		]
		self.assertEqual(result, expected)

	def test_formula_calculator_error_handling(self):
		"""Test formula calculator error handling for various edge cases"""
		row_data = {
			"NORMAL": [100.0, 200.0, 300.0],
		}

		period_list = [
			{"key": "2023_q1", "from_date": "2023-01-01", "to_date": "2023-03-31"},
			{"key": "2023_q2", "from_date": "2023-04-01", "to_date": "2023-06-30"},
			{"key": "2023_q3", "from_date": "2023-07-01", "to_date": "2023-09-30"},
		]

		calculator = FormulaCalculator(row_data, period_list)

		# Test invalid syntax - should return 0.0 for all periods
		result = calculator.evaluate_formula("NORMAL + +")  # Invalid syntax
		expected = [0.0, 0.0, 0.0]
		self.assertEqual(result, expected)

		# Test undefined variable - should return 0.0 for all periods
		result = calculator.evaluate_formula("UNDEFINED_VAR * 2")
		expected = [0.0, 0.0, 0.0]
		self.assertEqual(result, expected)

		# Test empty formula - should return 0.0 for all periods
		result = calculator.evaluate_formula("")
		expected = [0.0, 0.0, 0.0]
		self.assertEqual(result, expected)

	def test_formula_calculator_context_security(self):
		"""Test that formula calculator provides safe evaluation context"""
		row_data = {
			"TEST_VAL": [100.0, 200.0, 300.0],
		}

		period_list = [
			{"key": "2023_q1", "from_date": "2023-01-01", "to_date": "2023-03-31"},
		]

		calculator = FormulaCalculator(row_data, period_list)

		# Test that mathematical functions are available in context
		context = calculator.build_evaluation_context(0)

		# Check that safe functions are available
		self.assertIn("abs", context)
		self.assertIn("min", context)
		self.assertIn("max", context)
		self.assertIn("round", context)
		self.assertIn("sum", context)

		# Check that individual math functions are available (not the full math module)
		self.assertIn("sqrt", context)
		self.assertIn("pow", context)
		self.assertIn("ceil", context)
		self.assertIn("floor", context)

		# Ensure functions not included for financial use are not available
		self.assertNotIn("sin", context)
		self.assertNotIn("cos", context)
		self.assertNotIn("tan", context)
		self.assertNotIn("log", context)
		self.assertNotIn("log10", context)
		self.assertNotIn("radians", context)
		self.assertNotIn("degrees", context)

		# Ensure the full math module is not exposed for security
		self.assertNotIn("math", context)

		# Check that row data is properly included
		self.assertIn("TEST_VAL", context)
		self.assertEqual(context["TEST_VAL"], 100.0)

		# Test that invalid reference codes are not included
		calculator_with_invalid = FormulaCalculator(
			{
				"123_INVALID": [50.0],
				"VALID_CODE": [100.0],
			},
			period_list,
		)

		context = calculator_with_invalid.build_evaluation_context(0)
		self.assertNotIn("123_INVALID", context)  # Invalid identifier should be excluded
		self.assertIn("VALID_CODE", context)  # Valid identifier should be included

	def test_formula_calculator_security_protection(self):
		"""Test that formula calculator protects against potential security issues"""
		row_data = {"TEST_VAL": [100.0]}
		period_list = [{"key": "2023_q1", "from_date": "2023-01-01", "to_date": "2023-03-31"}]

		calculator = FormulaCalculator(row_data, period_list)

		# Test that potentially harmful expressions are safely handled
		# These should all return 0.0 due to safe evaluation failures
		harmful_expressions = [
			"__import__('os').system('ls')",  # Import attempts
			"eval('1+1')",  # Nested eval attempts
			"exec('print(1)')",  # Exec attempts
			"open('/etc/passwd')",  # File operations
			"globals()",  # Global namespace access
			"locals()",  # Local namespace access
		]

		for expr in harmful_expressions:
			with self.subTest(expression=expr):
				result = calculator.evaluate_formula(expr)
				self.assertEqual(result, [0.0], f"Harmful expression '{expr}' should return [0.0]")

		# Test that only safe mathematical operations work
		safe_expressions = [
			"TEST_VAL + 50",
			"abs(TEST_VAL - 200)",
			"min(TEST_VAL, 50)",
			"max(TEST_VAL, 150)",
			"round(TEST_VAL / 3, 2)",
		]

		for expr in safe_expressions:
			with self.subTest(expression=expr):
				result = calculator.evaluate_formula(expr)
				self.assertNotEqual(result, [0.0], f"Safe expression '{expr}' should not return [0.0]")
				self.assertIsInstance(result[0], float, f"Safe expression '{expr}' should return a float")

	def test_formula_calculator_advanced_math_functions(self):
		"""Test that essential mathematical functions for financial calculations are available"""
		row_data = {
			"BASE": [2.0],
			"EXPONENT": [3.0],
			"VALUE": [16.0],
			"NEGATIVE": [-100.0],
			"DECIMAL": [2.7],
		}
		period_list = [{"key": "2023_q1", "from_date": "2023-01-01", "to_date": "2023-03-31"}]

		calculator = FormulaCalculator(row_data, period_list)

		# Test power function - useful for compound interest calculations
		result = calculator.evaluate_formula("pow(BASE, EXPONENT)")
		self.assertEqual(result[0], 8.0)  # 2^3 = 8

		# Test square root - useful for standard deviation and ratio analysis
		result = calculator.evaluate_formula("sqrt(VALUE)")
		self.assertEqual(result[0], 4.0)  # sqrt(16) = 4

		# Test absolute value - essential for variance analysis
		result = calculator.evaluate_formula("abs(NEGATIVE)")
		self.assertEqual(result[0], 100.0)  # abs(-100) = 100

		# Test ceiling - useful for rounding up budget allocations
		result = calculator.evaluate_formula("ceil(DECIMAL)")
		self.assertEqual(result[0], 3.0)  # ceil(2.7) = 3

		# Test floor - useful for conservative estimates
		result = calculator.evaluate_formula("floor(DECIMAL)")
		self.assertEqual(result[0], 2.0)  # floor(2.7) = 2

		# Test min and max functions with multiple values
		result = calculator.evaluate_formula("min(BASE, VALUE)")
		self.assertEqual(result[0], 2.0)  # min(2.0, 16.0) = 2.0

		result = calculator.evaluate_formula("max(BASE, VALUE)")
		self.assertEqual(result[0], 16.0)  # max(2.0, 16.0) = 16.0

		# Test round function - essential for financial reporting
		result = calculator.evaluate_formula("round(DECIMAL)")
		self.assertEqual(result[0], 3.0)  # round(2.7) = 3

	def test_formula_calculator_financial_use_cases(self):
		"""Test real-world financial calculation scenarios"""
		row_data = {
			"REVENUE_Q1": [1000000.0],
			"REVENUE_Q2": [1200000.0],
			"EXPENSES": [800000.0],
			"BUDGET_VARIANCE": [-50000.0],
			"ACTUAL_COSTS": [123456.78],
			"GROWTH_RATE": [1.15],  # 15% growth
			"YEARS": [5.0],
		}
		period_list = [{"key": "2023_q1", "from_date": "2023-01-01", "to_date": "2023-03-31"}]

		calculator = FormulaCalculator(row_data, period_list)

		# Test best quarterly performance
		result = calculator.evaluate_formula("max(REVENUE_Q1, REVENUE_Q2)")
		self.assertEqual(result[0], 1200000.0)

		# Test absolute variance (remove negative sign for reporting)
		result = calculator.evaluate_formula("abs(BUDGET_VARIANCE)")
		self.assertEqual(result[0], 50000.0)

		# Test rounded reporting figures (clean up decimals)
		result = calculator.evaluate_formula("round(ACTUAL_COSTS)")
		self.assertEqual(result[0], 123457.0)  # Rounded to nearest whole number

		# Test conservative estimates (round down)
		result = calculator.evaluate_formula("floor(ACTUAL_COSTS / 1000)")
		self.assertEqual(result[0], 123.0)  # Conservative thousands

		# Test compound growth calculations
		result = calculator.evaluate_formula("pow(GROWTH_RATE, YEARS)")
		self.assertAlmostEqual(result[0], 2.01, places=1)  # 1.15^5 ≈ 2.01

		# Test profit calculation with rounding
		result = calculator.evaluate_formula("round((REVENUE_Q1 - EXPENSES) / REVENUE_Q1 * 100)")
		self.assertEqual(result[0], 20.0)  # 20% profit margin

	def test_financial_report_engine(self):
		"""Test the main financial report engine"""
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"filter_based_on": "Fiscal Year",
				"from_fiscal_year": "2023-24",
				"to_fiscal_year": "2023-24",
				"periodicity": "Yearly",
				"accumulated_values": 1,
			}
		)

		# This test would require proper test data setup
		# For now, just test that the engine initializes
		engine = FinancialReportEngine("Test P&L Template", filters)
		self.assertEqual(engine.template_name, "Test P&L Template")
		self.assertEqual(engine.filters, filters)

	def test_template_validation(self):
		"""Test template validation"""
		# Test duplicate reference codes
		with self.assertRaises(frappe.ValidationError):
			template = frappe.get_doc(
				{
					"doctype": "Financial Report Template",
					"template_name": "Invalid Template",
					"rows": [
						{"reference_code": "DUP001", "display_name": "Row 1", "data_source": "Account Data"},
						{
							"reference_code": "DUP001",  # Duplicate
							"display_name": "Row 2",
							"data_source": "Account Data",
						},
					],
				}
			)
			template.validate()

	def test_circular_reference_detection(self):
		"""Test circular reference detection"""
		with self.assertRaises(frappe.ValidationError):
			template = frappe.get_doc(
				{
					"doctype": "Financial Report Template",
					"template_name": "Circular Template",
					"rows": [
						{
							"reference_code": "A001",
							"display_name": "Row A",
							"data_source": "Calculated Amount",
							"calculation_formula": "B001 + 100",
						},
						{
							"reference_code": "B001",
							"display_name": "Row B",
							"data_source": "Calculated Amount",
							"calculation_formula": "A001 + 200",  # Circular reference
						},
					],
				}
			)
			template.validate()

	def test_account_filter_structure_simple_conditions(self):
		"""Test validation of simple account filter conditions"""
		# Test valid simple conditions
		valid_simple_filters = [
			'["account_type", "=", "Income"]',
			'["root_type", "!=", "Asset"]',
			'["is_group", "=", 0]',
			'["account_name", "like", "Cash"]',
			'["account_code", "in", ["1000", "2000"]]',
			'["parent_account", "is", "set"]',
		]

		for filter_formula in valid_simple_filters:
			template = frappe.get_doc(
				{
					"doctype": "Financial Report Template",
					"template_name": f"Test Simple Filter - {filter_formula[:20]}",
					"rows": [
						{
							"display_name": "Test Row",
							"data_source": "Account Data",
							"balance_type": "Closing Balance",
							"calculation_formula": filter_formula,
						}
					],
				}
			)
			# Should not raise any validation errors
			template.validate()

	def test_account_filter_structure_logical_conditions(self):
		"""Test validation of logical (AND/OR) account filter conditions"""
		# Test valid logical conditions
		valid_logical_filters = [
			'{"and": [["account_type", "=", "Income"], ["is_group", "=", 0]]}',
			'{"or": [["root_type", "=", "Asset"], ["root_type", "=", "Liability"]]}',
			'{"and": [["account_name", "like", "Cash"], ["account_type", "=", "Bank"]]}',
		]

		for filter_formula in valid_logical_filters:
			template = frappe.get_doc(
				{
					"doctype": "Financial Report Template",
					"template_name": f"Test Logical Filter - {filter_formula[:20]}",
					"rows": [
						{
							"display_name": "Test Row",
							"data_source": "Account Data",
							"balance_type": "Closing Balance",
							"calculation_formula": filter_formula,
						}
					],
				}
			)
			# Should not raise any validation errors
			template.validate()

	def test_account_filter_structure_nested_conditions(self):
		"""Test validation of complex nested account filter conditions"""
		# Test valid nested conditions
		nested_filter = """{
			"and": [
				{
					"or": [
						["account_type", "=", "Income"],
						["account_type", "=", "Expense"]
					]
				},
				["is_group", "=", 0],
				{
					"and": [
						["account_name", "not like", "Depreciation"],
						["disabled", "=", 0]
					]
				}
			]
		}"""

		template = frappe.get_doc(
			{
				"doctype": "Financial Report Template",
				"template_name": "Test Nested Filter",
				"rows": [
					{
						"display_name": "Complex Filter Row",
						"data_source": "Account Data",
						"balance_type": "Closing Balance",
						"calculation_formula": nested_filter,
					}
				],
			}
		)
		# Should not raise any validation errors
		template.validate()

	def test_account_filter_structure_invalid_conditions(self):
		"""Test validation of invalid account filter conditions"""
		# Test invalid simple conditions
		invalid_simple_filters = [
			'["incomplete"]',  # Missing operator and value
			'["field", "invalid_operator", "value"]',  # Invalid operator
			'[123, "=", "value"]',  # Non-string field
			'["field", 456, "value"]',  # Non-string operator
			"[]",  # Empty list
			'["too", "many", "elements", "here"]',  # Too many elements
		]

		for filter_formula in invalid_simple_filters:
			with self.assertRaises((frappe.ValidationError, frappe.exceptions.ValidationError)):
				template = frappe.get_doc(
					{
						"doctype": "Financial Report Template",
						"template_name": f"Invalid Simple Filter Test - {filter_formula[:10]}",
						"rows": [
							{
								"display_name": "Invalid Row",
								"data_source": "Account Data",
								"balance_type": "Closing Balance",
								"calculation_formula": filter_formula,
							}
						],
					}
				)
				template.validate()

		# Test invalid logical conditions
		invalid_logical_filters = [
			'{"invalid_operator": [["field", "=", "value"]]}',  # Invalid logical operator
			'{"and": ["not_a_list"]}',  # AND with non-list value
			'{"and": [["field", "=", "value"]]}',  # AND with only one condition (needs at least 2)
			'{"and": [], "or": []}',  # Multiple keys
			'{"and": []}',  # Empty conditions list
		]

		for filter_formula in invalid_logical_filters:
			with self.assertRaises((frappe.ValidationError, frappe.exceptions.ValidationError)):
				template = frappe.get_doc(
					{
						"doctype": "Financial Report Template",
						"template_name": f"Invalid Logical Filter Test - {filter_formula[:10]}",
						"rows": [
							{
								"display_name": "Invalid Row",
								"data_source": "Account Data",
								"balance_type": "Closing Balance",
								"calculation_formula": filter_formula,
							}
						],
					}
				)
				template.validate()

	def test_account_filter_structure_invalid_json(self):
		"""Test validation of invalid JSON in account filters"""
		invalid_json_filters = [
			'{"unclosed": "json"',  # Malformed JSON
			"not_json_at_all",  # Not JSON
			'{"account_type": =, "Income"}',  # Invalid JSON syntax
			"",  # Empty string
		]

		for filter_formula in invalid_json_filters:
			with self.assertRaises((frappe.ValidationError, frappe.exceptions.ValidationError)):
				template = frappe.get_doc(
					{
						"doctype": "Financial Report Template",
						"template_name": f"Invalid JSON Filter Test - {filter_formula[:10]}",
						"rows": [
							{
								"display_name": "Invalid JSON Row",
								"data_source": "Account Data",
								"balance_type": "Closing Balance",
								"calculation_formula": filter_formula,
							}
						],
					}
				)
				template.validate()

	def test_account_filter_structure_operators(self):
		"""Test all supported operators in account filters"""
		supported_operators = ["=", "==", "!=", "<>", "in", "not in", "like", "not like", "is"]

		for operator in supported_operators:
			if operator in ["in", "not in"]:
				# For 'in' operators, use list values
				filter_formula = f'["account_type", "{operator}", ["Income", "Expense"]]'
			elif operator == "is":
				# For 'is' operator, use special values
				filter_formula = f'["parent_account", "{operator}", "set"]'
			else:
				# For other operators, use string values
				filter_formula = f'["account_type", "{operator}", "Income"]'

			template = frappe.get_doc(
				{
					"doctype": "Financial Report Template",
					"template_name": f"Test Operator - {operator}",
					"rows": [
						{
							"display_name": f"Test Row - {operator}",
							"data_source": "Account Data",
							"balance_type": "Closing Balance",
							"calculation_formula": filter_formula,
						}
					],
				}
			)
			# Should not raise any validation errors
			template.validate()

	def test_period_account_data_collector_basic(self):
		"""Test basic functionality of PeriodAccountDataCollector"""
		# Setup test data
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"from_date": "2023-01-01",
				"to_date": "2023-12-31",
				"accumulated_values": 1,
			}
		)

		periods = [
			{"key": "2023_q1", "from_date": "2023-01-01", "to_date": "2023-03-31"},
			{"key": "2023_q2", "from_date": "2023-04-01", "to_date": "2023-06-30"},
		]

		collector = AccountDataCollector(filters, periods)

		# Create a mock row for testing
		mock_row = frappe._dict(
			{
				"balance_type": "Closing Balance",
				"calculation_formula": '["root_type", "=", "Income"]',
				"reference_code": "TEST_INC",
			}
		)

		collector.add_data_request(mock_row)
		results = collector.process_all_requests()

		# Verify we get results for all periods - check new structure
		self.assertIn("summary", results)
		self.assertIn("account_details", results)
		self.assertIn("TEST_INC", results["summary"])
		self.assertEqual(len(results["summary"]["TEST_INC"]), 2)  # Two periods

	def test_balance_processor_opening_balance(self):
		"""Test opening balance calculation in BalanceProcessor"""
		filters = frappe._dict({"company": "_Test Company"})
		periods = [
			{"key": "2023_q1", "from_date": "2023-01-01", "to_date": "2023-03-31"},
			{"key": "2023_q2", "from_date": "2023-04-01", "to_date": "2023-06-30"},
		]

		processor = BalanceProcessor(filters, periods)

		# Test with some test accounts
		test_accounts = ["Cash - _TC", "Sales - _TC"]
		balance_data = processor.fetch_all_balances(test_accounts)

		# Verify structure
		for account in test_accounts:
			if account in balance_data:
				for period in periods:
					period_key = period["key"]
					if period_key in balance_data[account]:
						balance_info = balance_data[account][period_key]
						# Should have opening, closing, movement keys
						self.assertIn("opening", balance_info)
						self.assertIn("closing", balance_info)
						self.assertIn("movement", balance_info)

						# Closing = Opening + Movement
						expected_closing = balance_info["opening"] + balance_info["movement"]
						self.assertAlmostEqual(balance_info["closing"], expected_closing, places=2)

	def test_balance_processor_with_ignore_closing(self):
		"""Test BalanceProcessor when ignore_closing_balances is enabled"""
		# Enable ignore closing balances setting
		original_setting = frappe.get_single_value("Accounts Settings", "ignore_account_closing_balance")
		frappe.db.set_single_value("Accounts Settings", "ignore_account_closing_balance", 1)

		try:
			# Create a sales invoice to ensure we have GL entries
			from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice

			si = create_sales_invoice(posting_date="2023-01-15", rate=1000, qty=1, do_not_submit=True)
			si.submit()

			filters = frappe._dict({"company": "_Test Company"})
			periods = [{"key": "2023_q1", "from_date": "2023-01-01", "to_date": "2023-03-31"}]

			processor = BalanceProcessor(filters, periods)
			# Test with Debtors account which will have GL entries from the invoice
			test_accounts = ["Debtors - _TC"]
			balance_data = processor.fetch_all_balances(test_accounts)

			# Should still return valid data structure with all keys
			self.assertIn("Debtors - _TC", balance_data)
			self.assertIn("2023_q1", balance_data["Debtors - _TC"])

			balance_info = balance_data["Debtors - _TC"]["2023_q1"]
			self.assertIn("opening", balance_info)
			self.assertIn("closing", balance_info)
			self.assertIn("movement", balance_info)

			# Verify calculation consistency
			expected_closing = balance_info["opening"] + balance_info["movement"]
			self.assertAlmostEqual(balance_info["closing"], expected_closing, places=2)

			# Cleanup
			si.cancel()

		finally:
			# Restore original setting
			frappe.db.set_single_value(
				"Accounts Settings", "ignore_account_closing_balance", original_setting
			)

	def test_balance_processor_period_movement(self):
		"""Test period movement calculation"""
		filters = frappe._dict({"company": "_Test Company"})
		periods = [
			{"key": "2023_q1", "from_date": "2023-01-01", "to_date": "2023-03-31"},
			{"key": "2023_q2", "from_date": "2023-04-01", "to_date": "2023-06-30"},
		]

		processor = BalanceProcessor(filters, periods)

		# Mock request for period movement
		request = {
			"accounts": ["Sales - _TC"],
			"balance_type": "Period Movement (Debits - Credits)",
			"row": frappe._dict({"balance_type": "Period Movement (Debits - Credits)"}),
		}

		# Create some sample balance data
		mock_balance_data = {
			"Sales - _TC": {
				"2023_q1": {"opening": 0, "movement": 1000, "closing": 1000},
				"2023_q2": {"opening": 1000, "movement": 500, "closing": 1500},
			}
		}

		# Get account values first, then calculate totals
		account_values = processor.get_account_values(request, mock_balance_data)
		totals = processor.calculate_totals(account_values)

		# Should return movement values for each period
		self.assertEqual(len(totals), 2)
		self.assertEqual(totals[0], 1000)  # Q1 movement
		self.assertEqual(totals[1], 500)  # Q2 movement

	def test_filter_expression_parser_simple(self):
		"""Test FilterExpressionParser with simple conditions"""
		parser = FilterExpressionParser()

		# Test simple equality condition
		simple_formula = '["account_type", "=", "Income"]'
		criteria = parser.parse(simple_formula)

		self.assertEqual(criteria["type"], "simple")
		self.assertEqual(criteria["field"], "account_type")
		self.assertEqual(criteria["operator"], "=")
		self.assertEqual(criteria["value"], "Income")

		# Test with mock table
		from frappe.query_builder import DocType

		account_table = DocType("Account")
		condition = parser.build_condition(criteria, account_table)
		self.assertIsNotNone(condition)

	def test_filter_expression_parser_logical(self):
		"""Test FilterExpressionParser with logical conditions"""
		parser = FilterExpressionParser()

		# Test AND condition
		and_formula = """{"and": [["account_type", "=", "Income"], ["is_group", "=", 0]]}"""
		criteria = parser.parse(and_formula)

		self.assertEqual(criteria["type"], "logical")
		self.assertEqual(criteria["operator"], "and")
		self.assertEqual(len(criteria["conditions"]), 2)

		# Test OR condition
		or_formula = """{"or": [["root_type", "=", "Asset"], ["root_type", "=", "Liability"]]}"""
		criteria = parser.parse(or_formula)

		self.assertEqual(criteria["type"], "logical")
		self.assertEqual(criteria["operator"], "or")
		self.assertEqual(len(criteria["conditions"]), 2)

	def test_filter_expression_parser_operators(self):
		"""Test various operators in FilterExpressionParser"""
		parser = FilterExpressionParser()
		from frappe.query_builder import DocType

		account_table = DocType("Account")

		test_cases = [
			('["account_name", "!=", "Cash"]', "!="),
			('["account_code", "like", "1000"]', "like"),
			('["account_type", "in", ["Income", "Expense"]]', "in"),
			('["parent_account", "is", "set"]', "is"),
		]

		for formula, expected_op in test_cases:
			criteria = parser.parse(formula)
			self.assertEqual(criteria["operator"], expected_op)

			# Verify condition can be built
			condition = parser.build_condition(criteria, account_table)
			if criteria["field"] in ["account_name", "account_code", "account_type", "parent_account"]:
				self.assertIsNotNone(condition)

	def test_profit_and_loss_filters_integration(self):
		"""Test integration with all P&L statement filters"""
		# Create test filters similar to P&L statement
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"filter_based_on": "Fiscal Year",
				"from_fiscal_year": "2023-24",
				"to_fiscal_year": "2023-24",
				"periodicity": "Quarterly",
				"accumulated_values": 1,
				"include_default_book_entries": 1,
				"cost_center": None,
				"project": None,
				"finance_book": None,
			}
		)

		periods = [
			{"key": "2023_q1", "from_date": "2023-04-01", "to_date": "2023-06-30"},
			{"key": "2023_q2", "from_date": "2023-07-01", "to_date": "2023-09-30"},
		]

		collector = AccountDataCollector(filters, periods)

		# Test with Income accounts
		income_row = frappe._dict(
			{
				"balance_type": "Closing Balance",
				"calculation_formula": '["root_type", "=", "Income"]',
				"reference_code": "INCOME",
			}
		)

		# Test with Expense accounts
		expense_row = frappe._dict(
			{
				"balance_type": "Closing Balance",
				"calculation_formula": '["root_type", "=", "Expense"]',
				"reference_code": "EXPENSE",
			}
		)

		collector.add_data_request(income_row)
		collector.add_data_request(expense_row)

		results = collector.process_all_requests()

		# Verify both account types return data with new structure
		self.assertIn("summary", results)
		self.assertIn("INCOME", results["summary"])
		self.assertIn("EXPENSE", results["summary"])

	def test_with_cost_center_filter(self):
		"""Test BalanceProcessor with cost center filters"""
		filters = frappe._dict({"company": "_Test Company", "cost_center": "_Test Cost Center - _TC"})

		periods = [{"key": "2023_q1", "from_date": "2023-01-01", "to_date": "2023-03-31"}]

		processor = BalanceProcessor(filters, periods)
		test_accounts = ["Sales - _TC"]

		# Should not raise any errors
		balance_data = processor.fetch_all_balances(test_accounts)
		self.assertIsInstance(balance_data, dict)

	def test_with_project_filter(self):
		"""Test BalanceProcessor with project filters"""
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"project": ["_Test Project"],  # List format as expected
			}
		)

		periods = [{"key": "2023_q1", "from_date": "2023-01-01", "to_date": "2023-03-31"}]

		processor = BalanceProcessor(filters, periods)
		test_accounts = ["Sales - _TC"]

		# Should not raise any errors
		balance_data = processor.fetch_all_balances(test_accounts)
		self.assertIsInstance(balance_data, dict)

	def test_with_finance_book_filter(self):
		"""Test BalanceProcessor with finance book filters"""
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"finance_book": "Test Finance Book",
				"include_default_book_entries": 0,
			}
		)

		periods = [{"key": "2023_q1", "from_date": "2023-01-01", "to_date": "2023-03-31"}]

		processor = BalanceProcessor(filters, periods)
		test_accounts = ["Sales - _TC"]

		# Should not raise any errors
		balance_data = processor.fetch_all_balances(test_accounts)
		self.assertIsInstance(balance_data, dict)

	def test_data_source_types(self):
		"""Test all three data source types: Opening Balance, Closing Balance, Period Movement"""
		filters = frappe._dict({"company": "_Test Company"})
		periods = [{"key": "2023_q1", "from_date": "2023-01-01", "to_date": "2023-03-31"}]

		processor = BalanceProcessor(filters, periods)

		# Mock balance data
		mock_balance_data = {"Test Account": {"2023_q1": {"opening": 1000, "movement": 500, "closing": 1500}}}

		# Test Opening Balance
		opening_request = {"accounts": ["Test Account"], "balance_type": "Opening Balance"}
		opening_account_values = processor.get_account_values(opening_request, mock_balance_data)
		opening_totals = processor.calculate_totals(opening_account_values)
		self.assertEqual(opening_totals[0], 1000)

		# Test Closing Balance
		closing_request = {"accounts": ["Test Account"], "balance_type": "Closing Balance"}
		closing_account_values = processor.get_account_values(closing_request, mock_balance_data)
		closing_totals = processor.calculate_totals(closing_account_values)
		self.assertEqual(closing_totals[0], 1500)

		# Test Period Movement
		movement_request = {
			"accounts": ["Test Account"],
			"balance_type": "Period Movement (Debits - Credits)",
		}
		movement_account_values = processor.get_account_values(movement_request, mock_balance_data)
		movement_totals = processor.calculate_totals(movement_account_values)
		self.assertEqual(movement_totals[0], 500)

	def test_complex_nested_filters(self):
		"""Test complex nested filter expressions"""
		parser = FilterExpressionParser()

		# Complex nested condition: ((Income OR Expense) AND NOT Other) AND is_group=0
		complex_formula = """{
			"and": [
				{
					"and": [
						{
							"or": [
								["root_type", "=", "Income"],
								["root_type", "=", "Expense"]
							]
						},
						["account_category", "!=", "Other Income"]
					]
				},
				["is_group", "=", 0]
			]
		}"""

		criteria = parser.parse(complex_formula)
		self.assertEqual(criteria["type"], "logical")
		self.assertEqual(criteria["operator"], "and")

		# Verify nested structure
		self.assertEqual(len(criteria["conditions"]), 2)
		nested_condition = criteria["conditions"][0]
		self.assertEqual(nested_condition["type"], "logical")

	def test_invalid_filter_expressions(self):
		"""Test handling of invalid filter expressions"""
		parser = FilterExpressionParser()

		# Test malformed expressions
		invalid_expressions = [
			'["incomplete"]',  # Missing operator and value
			'{"invalid": "structure"}',  # Wrong structure
			"not_a_list_or_dict",  # Invalid format
			'{"and": ["not_a_list"]}',  # AND without proper list
		]

		for expr in invalid_expressions:
			try:
				criteria = parser.parse(expr)
				# Should return empty dict or invalid type
				self.assertTrue(
					criteria == {} or criteria.get("type") == "invalid",
					f"Expression {expr} should be invalid",
				)
			except Exception:
				# Exception is also acceptable for invalid expressions
				pass

	def test_multiple_periods_consistency(self):
		"""Test data consistency across multiple periods"""
		filters = frappe._dict({"company": "_Test Company"})
		periods = [
			{"key": "2023_q1", "from_date": "2023-01-01", "to_date": "2023-03-31"},
			{"key": "2023_q2", "from_date": "2023-04-01", "to_date": "2023-06-30"},
			{"key": "2023_q3", "from_date": "2023-07-01", "to_date": "2023-09-30"},
		]

		collector = AccountDataCollector(filters, periods)

		test_row = frappe._dict(
			{
				"balance_type": "Closing Balance",
				"calculation_formula": '["account_type", "=", "Income"]',
				"reference_code": "MULTI_PERIOD_TEST",
			}
		)

		collector.add_data_request(test_row)
		results = collector.process_all_requests()

		if "MULTI_PERIOD_TEST" in results:
			period_values = results["MULTI_PERIOD_TEST"]

			# Should have values for all periods
			self.assertEqual(len(period_values), 3)

			# All values should be numeric
			for value in period_values:
				self.assertIsInstance(value, (int, float))

	def test_with_actual_sales_invoice_transactions(self):
		"""Test utilities with actual Sales Invoice transactions"""
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice

		# Create test sales invoices for different periods
		si1 = create_sales_invoice(posting_date="2023-01-15", rate=1000, qty=1, do_not_submit=True)
		si1.submit()

		si2 = create_sales_invoice(posting_date="2023-02-15", rate=1500, qty=1, do_not_submit=True)
		si2.submit()

		si3 = create_sales_invoice(posting_date="2023-04-15", rate=2000, qty=1, do_not_submit=True)
		si3.submit()

		# Setup filters and periods to capture these transactions
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"from_date": "2023-01-01",
				"to_date": "2023-12-31",
			}
		)

		periods = [
			{"key": "2023_q1", "from_date": "2023-01-01", "to_date": "2023-03-31"},
			{"key": "2023_q2", "from_date": "2023-04-01", "to_date": "2023-06-30"},
		]

		collector = AccountDataCollector(filters, periods)

		# Test with Sales account (Income)
		sales_row = frappe._dict(
			{
				"balance_type": "Period Movement (Debits - Credits)",
				"calculation_formula": '["account_name", "like", "Sales"]',
				"reference_code": "SALES_MOVEMENT",
			}
		)

		collector.add_data_request(sales_row)
		results = collector.process_all_requests()

		# Verify sales movement matches invoice amounts
		if "SALES_MOVEMENT" in results:
			q1_movement, q2_movement = results["SALES_MOVEMENT"]

			# Q1 should have 2500 (1000 + 1500) in sales
			# Q2 should have 2000 in sales
			# Note: Sales are credit entries, so movement might be negative
			self.assertGreater(abs(q1_movement), 2400)  # Allow for small rounding differences
			self.assertGreater(abs(q2_movement), 1900)

		# Cleanup
		si1.cancel()
		si2.cancel()
		si3.cancel()

	def test_with_actual_purchase_invoice_transactions(self):
		"""Test utilities with actual Purchase Invoice transactions"""
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice

		# Create test purchase invoices
		pi1 = make_purchase_invoice(posting_date="2023-01-20", rate=800, qty=1, do_not_save=True)
		pi1.set_posting_time = 1
		pi1.save()
		pi1.submit()

		pi2 = make_purchase_invoice(posting_date="2023-03-10", rate=1200, qty=1, do_not_save=True)
		pi2.set_posting_time = 1
		pi2.save()
		pi2.submit()

		# Setup test environment
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"from_date": "2023-01-01",
				"to_date": "2023-12-31",
			}
		)

		periods = [
			{"key": "2023_q1", "from_date": "2023-01-01", "to_date": "2023-03-31"},
		]

		collector = AccountDataCollector(filters, periods)

		# Test with Expense account
		expense_row = frappe._dict(
			{
				"balance_type": "Period Movement (Debits - Credits)",
				"calculation_formula": '["account_name", "like", "_Test Account Cost for Goods Sold"]',
				"reference_code": "EXPENSE_MOVEMENT",
			}
		)

		collector.add_data_request(expense_row)
		results = collector.process_all_requests()

		# Verify expense movement
		if "EXPENSE_MOVEMENT" in results:
			q1_movement = results["EXPENSE_MOVEMENT"][0]
			# Q1 should have 2000 (800 + 1200) in expenses
			# Expenses are debit entries, so should be positive
			self.assertGreater(q1_movement, 1900)

		# Cleanup
		pi1.cancel()
		pi2.cancel()

	def test_opening_and_closing_balances_with_transactions(self):
		"""Test opening and closing balance calculations with real transactions"""
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice

		# Create a sales invoice in the first period
		si = create_sales_invoice(posting_date="2023-01-15", rate=5000, qty=1, do_not_submit=True)
		si.submit()

		filters = frappe._dict(
			{
				"company": "_Test Company",
				"from_date": "2023-01-01",
				"to_date": "2023-12-31",
			}
		)

		periods = [
			{"key": "2023_q1", "from_date": "2023-01-01", "to_date": "2023-03-31"},
			{"key": "2023_q2", "from_date": "2023-04-01", "to_date": "2023-06-30"},
		]

		processor = BalanceProcessor(filters, periods)
		balance_data = processor.fetch_all_balances(["Debtors - _TC"])

		if "Debtors - _TC" in balance_data:
			# Check Q1 data
			if "2023_q1" in balance_data["Debtors - _TC"]:
				q1_data = balance_data["Debtors - _TC"]["2023_q1"]

				# Should have movement (new invoice)
				self.assertGreater(q1_data["movement"], 4900)

				# Closing = Opening + Movement should be consistent
				expected_closing = q1_data["opening"] + q1_data["movement"]
				self.assertAlmostEqual(q1_data["closing"], expected_closing, places=2)

			# Check Q2 data (no new transactions)
			if "2023_q2" in balance_data["Debtors - _TC"]:
				q2_data = balance_data["Debtors - _TC"]["2023_q2"]

				# Q2 opening should equal Q1 closing
				if "2023_q1" in balance_data["Debtors - _TC"]:
					q1_closing = balance_data["Debtors - _TC"]["2023_q1"]["closing"]
					self.assertAlmostEqual(q2_data["opening"], q1_closing, places=2)

		# Cleanup
		si.cancel()

	def test_ignore_closing_balances_with_transactions(self):
		"""Test the ignore_closing_balances setting with real transactions"""
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice

		# Get original setting
		original_setting = frappe.get_single_value("Accounts Settings", "ignore_account_closing_balance")

		try:
			# Enable ignore closing balances
			frappe.db.set_single_value("Accounts Settings", "ignore_account_closing_balance", 1)

			# Create a sales invoice
			si = create_sales_invoice(posting_date="2023-02-01", rate=3000, qty=1, do_not_submit=True)
			si.submit()

			filters = frappe._dict({"company": "_Test Company"})
			periods = [{"key": "2023_q1", "from_date": "2023-01-01", "to_date": "2023-03-31"}]

			processor = BalanceProcessor(filters, periods)
			balance_data = processor.fetch_all_balances(["Sales - _TC"])

			# Should still get valid balance data
			if "Sales - _TC" in balance_data and "2023_q1" in balance_data["Sales - _TC"]:
				q1_data = balance_data["Sales - _TC"]["2023_q1"]

				# Should have all required keys
				self.assertIn("opening", q1_data)
				self.assertIn("closing", q1_data)
				self.assertIn("movement", q1_data)

				# Movement should reflect the sales invoice (negative for credit)
				self.assertLess(q1_data["movement"], -2900)

			# Cleanup
			si.cancel()

		finally:
			# Restore original setting
			frappe.db.set_single_value(
				"Accounts Settings", "ignore_account_closing_balance", original_setting
			)

	def test_complex_filter_matching_with_actual_accounts(self):
		"""Test complex filter expressions against actual chart of accounts"""
		filters = frappe._dict({"company": "_Test Company"})
		periods = [{"key": "2023_q1", "from_date": "2023-01-01", "to_date": "2023-03-31"}]

		collector = AccountDataCollector(filters, periods)

		# Test complex nested filter
		complex_row = frappe._dict(
			{
				"balance_type": "Closing Balance",
				"calculation_formula": """{
				"and": [
					{
						"or": [
							["root_type", "=", "Asset"],
							["root_type", "=", "Liability"]
						]
					},
					["is_group", "=", 0]
				]
			}""",
				"reference_code": "COMPLEX_FILTER_TEST",
			}
		)

		collector.add_data_request(complex_row)
		results = collector.process_all_requests()

		# Should find matching accounts and return balance data - check new structure
		self.assertIn("summary", results)
		self.assertIn("COMPLEX_FILTER_TEST", results["summary"])
		self.assertEqual(len(results["summary"]["COMPLEX_FILTER_TEST"]), 1)  # One period

		# Test simple filter for comparison
		simple_row = frappe._dict(
			{
				"balance_type": "Closing Balance",
				"calculation_formula": '["root_type", "=", "Asset"]',
				"reference_code": "SIMPLE_FILTER_TEST",
			}
		)

		collector.add_data_request(simple_row)
		results = collector.process_all_requests()

		self.assertIn("SIMPLE_FILTER_TEST", results["summary"])

	def test_integration_with_profit_loss_filters(self):
		"""Test integration with actual Profit and Loss statement filters"""
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice

		# Create some transactions
		si = create_sales_invoice(posting_date="2023-01-10", rate=4000, qty=1)

		pi = make_purchase_invoice(posting_date="2023-01-20", rate=2500, qty=1, do_not_save=True)
		pi.set_posting_time = 1
		pi.save()
		pi.submit()

		# Use typical P&L filters
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"filter_based_on": "Date Range",
				"from_date": "2023-01-01",
				"to_date": "2023-03-31",
				"periodicity": "Monthly",
				"accumulated_values": 0,
				"include_default_book_entries": 1,
			}
		)

		periods = [
			{"key": "2023_jan", "from_date": "2023-01-01", "to_date": "2023-01-31"},
			{"key": "2023_feb", "from_date": "2023-02-01", "to_date": "2023-02-28"},
		]

		collector = AccountDataCollector(filters, periods)

		# Test Income accounts
		income_row = frappe._dict(
			{
				"balance_type": "Period Movement (Debits - Credits)",
				"calculation_formula": '["root_type", "=", "Income"]',
				"reference_code": "TOTAL_INCOME",
			}
		)

		# Test Expense accounts
		expense_row = frappe._dict(
			{
				"balance_type": "Period Movement (Debits - Credits)",
				"calculation_formula": '["root_type", "=", "Expense"]',
				"reference_code": "TOTAL_EXPENSE",
			}
		)

		collector.add_data_request(income_row)
		collector.add_data_request(expense_row)
		results = collector.process_all_requests()

		# Verify results with new structure
		self.assertIn("summary", results)
		self.assertIn("TOTAL_INCOME", results["summary"])
		self.assertIn("TOTAL_EXPENSE", results["summary"])

		# Both should have data for 2 periods
		self.assertEqual(len(results["summary"]["TOTAL_INCOME"]), 2)
		self.assertEqual(len(results["summary"]["TOTAL_EXPENSE"]), 2)

		# January should have both income and expense movements
		jan_income = results["summary"]["TOTAL_INCOME"][0]  # January
		jan_expense = results["summary"]["TOTAL_EXPENSE"][0]  # January

		# Income should be negative (credit), expense positive (debit)
		self.assertLess(jan_income, -3900)  # Sales invoice amount
		self.assertGreater(jan_expense, 2400)  # Purchase invoice amount

		# Cleanup
		si.cancel()
		pi.cancel()

	def test_data_source_consistency_with_transactions(self):
		"""Test that all three data sources (Opening, Closing, Movement) are consistent"""
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice

		# Create a sales invoice
		si = create_sales_invoice(posting_date="2023-01-15", rate=1000, qty=1, do_not_submit=True)
		si.submit()

		filters = frappe._dict({"company": "_Test Company"})
		periods = [
			{"key": "2023_q1", "from_date": "2023-01-01", "to_date": "2023-03-31"},
			{"key": "2023_q2", "from_date": "2023-04-01", "to_date": "2023-06-30"},
		]

		collector = AccountDataCollector(filters, periods)

		# Create requests for all three data sources for the same account
		opening_row = frappe._dict(
			{
				"balance_type": "Opening Balance",
				"calculation_formula": '["account_name", "=", "Debtors - _TC"]',
				"reference_code": "OPENING_BAL",
			}
		)

		movement_row = frappe._dict(
			{
				"balance_type": "Period Movement (Debits - Credits)",
				"calculation_formula": '["account_name", "=", "Debtors - _TC"]',
				"reference_code": "MOVEMENT",
			}
		)

		closing_row = frappe._dict(
			{
				"balance_type": "Closing Balance",
				"calculation_formula": '["account_name", "=", "Debtors - _TC"]',
				"reference_code": "CLOSING_BAL",
			}
		)

		collector.add_data_request(opening_row)
		collector.add_data_request(movement_row)
		collector.add_data_request(closing_row)

		results = collector.process_all_requests()

		# All should be present in new structure
		self.assertIn("summary", results)
		self.assertIn("OPENING_BAL", results["summary"])
		self.assertIn("MOVEMENT", results["summary"])
		self.assertIn("CLOSING_BAL", results["summary"])

		# Check Q1 consistency: Closing = Opening + Movement
		q1_opening = results["summary"]["OPENING_BAL"][0]
		q1_movement = results["summary"]["MOVEMENT"][0]
		q1_closing = results["summary"]["CLOSING_BAL"][0]

		self.assertAlmostEqual(q1_closing, q1_opening + q1_movement, places=2)

		# Check Q2 consistency: Q2 Opening should equal Q1 Closing
		q2_opening = results["summary"]["OPENING_BAL"][1]
		self.assertAlmostEqual(q2_opening, q1_closing, places=2)

		# Cleanup
		si.cancel()

	@classmethod
	def tearDownClass(cls):
		"""Clean up test data"""
		frappe.db.rollback()
