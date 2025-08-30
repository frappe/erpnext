# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt

from erpnext.accounts.doctype.financial_report_template.financial_report_engine import (
	AccountData,
	DataCollector,
	DependencyResolver,
	FilterExpressionParser,
	FinancialQueryBuilder,
	FormulaCalculator,
	PeriodValue,
)
from erpnext.accounts.doctype.financial_report_template.test_financial_report_template import (
	FinancialReportTemplateTestCase,
)
from erpnext.accounts.utils import get_currency_precision

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]


class TestDependencyResolver(FinancialReportTemplateTestCase):
	"""Test cases for DependencyResolver class"""

	# 1. BASIC FUNCTIONALITY
	def test_basic_processing_order(self):
		resolver = DependencyResolver(self.test_template)
		order = resolver.get_processing_order()

		# Should process account rows before formula rows
		account_indices = [i for i, row in enumerate(order) if row.data_source == "Account Data"]
		formula_indices = [i for i, row in enumerate(order) if row.data_source == "Calculated Amount"]

		self.assertTrue(all(ai < fi for ai in account_indices for fi in formula_indices))

	def test_simple_dependency_resolution(self):
		# Create test rows with dependencies
		test_rows = [
			{
				"reference_code": "A001",
				"display_name": "Base Account",
				"data_source": "Account Data",
				"balance_type": "Closing Balance",
				"calculation_formula": '["account_type", "=", "Income"]',
			},
			{
				"reference_code": "B001",
				"display_name": "Calculated Row",
				"data_source": "Calculated Amount",
				"calculation_formula": "A001 * 2",
			},
		]

		test_template = FinancialReportTemplateTestCase.create_test_template_with_rows(test_rows)
		resolver = DependencyResolver(test_template)

		# Check dependencies were correctly identified
		self.assertIn("B001", resolver.dependencies)
		self.assertEqual(resolver.dependencies["B001"], ["A001"])

		# Check processing order
		order = resolver.get_processing_order()
		a001_index = next(i for i, row in enumerate(order) if row.reference_code == "A001")
		b001_index = next(i for i, row in enumerate(order) if row.reference_code == "B001")

		self.assertLess(a001_index, b001_index, "A001 should be processed before B001")

	# 2. DEPENDENCY PATTERNS
	def test_multiple_dependencies(self):
		test_rows = [
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

		test_template = FinancialReportTemplateTestCase.create_test_template_with_rows(test_rows)
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

	def test_chain_dependencies(self):
		"""Test dependency resolution with chain of dependencies (A -> B -> C -> D)"""
		test_rows = [
			{
				"reference_code": "A001",
				"display_name": "Base",
				"data_source": "Account Data",
				"balance_type": "Closing Balance",
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

		test_template = FinancialReportTemplateTestCase.create_test_template_with_rows(test_rows)
		resolver = DependencyResolver(test_template)
		order = resolver.get_processing_order()
		positions = {row.reference_code: i for i, row in enumerate(order) if row.reference_code}

		# Verify chain order
		self.assertLess(positions["A001"], positions["B001"])
		self.assertLess(positions["B001"], positions["C001"])
		self.assertLess(positions["C001"], positions["D001"])

	def test_diamond_dependency_pattern(self):
		"""Test Diamond Dependency Pattern - A → B, A → C, and both B,C → D"""
		test_rows = [
			{
				"reference_code": "A001",
				"display_name": "Base Data",
				"data_source": "Account Data",
				"balance_type": "Closing Balance",
				"calculation_formula": '["account_type", "=", "Income"]',
			},
			{
				"reference_code": "B001",
				"display_name": "Branch B",
				"data_source": "Calculated Amount",
				"calculation_formula": "A001 * 0.6",  # B depends on A
			},
			{
				"reference_code": "C001",
				"display_name": "Branch C",
				"data_source": "Calculated Amount",
				"calculation_formula": "A001 * 0.4",  # C depends on A
			},
			{
				"reference_code": "D001",
				"display_name": "Final Result",
				"data_source": "Calculated Amount",
				"calculation_formula": "B001 + C001",  # D depends on both B and C
			},
		]

		test_template = FinancialReportTemplateTestCase.create_test_template_with_rows(test_rows)
		resolver = DependencyResolver(test_template)
		order = resolver.get_processing_order()
		positions = {row.reference_code: i for i, row in enumerate(order)}

		# A should be processed first
		self.assertLess(positions["A001"], positions["B001"])
		self.assertLess(positions["A001"], positions["C001"])
		self.assertLess(positions["A001"], positions["D001"])

		# Both B and C should be processed before D
		self.assertLess(positions["B001"], positions["D001"])
		self.assertLess(positions["C001"], positions["D001"])

		# Verify D has correct dependencies
		self.assertEqual(set(resolver.dependencies["D001"]), {"B001", "C001"})

	def test_independent_formula_row_groups(self):
		test_rows = [
			# Chain 1: A → B → C
			{
				"reference_code": "A001",
				"display_name": "Chain 1 Base",
				"data_source": "Account Data",
				"balance_type": "Closing Balance",
				"calculation_formula": '["account_type", "=", "Asset"]',
			},
			{
				"reference_code": "B001",
				"display_name": "Chain 1 Level 2",
				"data_source": "Calculated Amount",
				"calculation_formula": "A001 * 1.1",
			},
			{
				"reference_code": "C001",
				"display_name": "Chain 1 Final",
				"data_source": "Calculated Amount",
				"calculation_formula": "B001 + 100",
			},
			# Chain 2: X → Y → Z (independent)
			{
				"reference_code": "X001",
				"display_name": "Chain 2 Base",
				"data_source": "Account Data",
				"balance_type": "Closing Balance",
				"calculation_formula": '["account_type", "=", "Liability"]',
			},
			{
				"reference_code": "Y001",
				"display_name": "Chain 2 Level 2",
				"data_source": "Calculated Amount",
				"calculation_formula": "X001 * 0.9",
			},
			{
				"reference_code": "Z001",
				"display_name": "Chain 2 Final",
				"data_source": "Calculated Amount",
				"calculation_formula": "Y001 - 50",
			},
		]

		test_template = FinancialReportTemplateTestCase.create_test_template_with_rows(test_rows)
		resolver = DependencyResolver(test_template)
		order = resolver.get_processing_order()
		positions = {row.reference_code: i for i, row in enumerate(order)}

		# Verify Chain 1 order
		self.assertLess(positions["A001"], positions["B001"])
		self.assertLess(positions["B001"], positions["C001"])

		# Verify Chain 2 order
		self.assertLess(positions["X001"], positions["Y001"])
		self.assertLess(positions["Y001"], positions["Z001"])

		# Verify chains are independent (no cross-dependencies)
		chain1_codes = {"A001", "B001", "C001"}
		chain2_codes = {"X001", "Y001", "Z001"}

		for code in chain1_codes:
			if code in resolver.dependencies:
				deps = set(resolver.dependencies[code])
				self.assertFalse(deps.intersection(chain2_codes), f"{code} should not depend on chain 2")

		for code in chain2_codes:
			if code in resolver.dependencies:
				deps = set(resolver.dependencies[code])
				self.assertFalse(deps.intersection(chain1_codes), f"{code} should not depend on chain 1")

	# 3. DATA SOURCE PROCESSING
	def test_process_mixed_data_sources(self):
		test_rows = [
			{
				"reference_code": "CALC001",
				"display_name": "Calculated",
				"data_source": "Calculated Amount",
				"calculation_formula": "ACC001 + 100",
			},
			{
				"reference_code": None,
				"display_name": "Spacing",
				"data_source": "Blank Line",
			},
			{
				"reference_code": "ACC001",
				"display_name": "Account",
				"data_source": "Account Data",
				"balance_type": "Closing Balance",
				"calculation_formula": '["account_type", "=", "Income"]',
			},
			{
				"reference_code": None,
				"display_name": "Custom",
				"data_source": "Custom API",
			},
		]

		test_template = FinancialReportTemplateTestCase.create_test_template_with_rows(test_rows)
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

	def test_api_to_formula_dependencies(self):
		test_rows = [
			{
				"reference_code": "API001",
				"display_name": "Custom API Result",
				"data_source": "Custom API",
			},
			{
				"reference_code": "ACC001",
				"display_name": "Account Data",
				"data_source": "Account Data",
				"balance_type": "Closing Balance",
				"calculation_formula": '["account_type", "=", "Income"]',
			},
			{
				"reference_code": "CALC001",
				"display_name": "Calculated Result",
				"data_source": "Calculated Amount",
				"calculation_formula": "API001 + ACC001",
			},
		]

		test_template = FinancialReportTemplateTestCase.create_test_template_with_rows(test_rows)
		resolver = DependencyResolver(test_template)
		order = resolver.get_processing_order()
		positions = {row.reference_code: i for i, row in enumerate(order)}

		# API001 should be processed before CALC001
		self.assertLess(positions["API001"], positions["CALC001"])
		# ACC001 should be processed before CALC001
		self.assertLess(positions["ACC001"], positions["CALC001"])
		# API001 should be processed before ACC001 (API rows come first)
		self.assertLess(positions["API001"], positions["ACC001"])

	def test_cross_datasource_dependencies(self):
		test_rows = [
			{
				"reference_code": "API001",
				"display_name": "API Data",
				"data_source": "Custom API",
			},
			{
				"reference_code": "ACC001",
				"display_name": "Account Total",
				"data_source": "Account Data",
				"balance_type": "Closing Balance",
				"calculation_formula": '["account_type", "=", "Income"]',
			},
			{
				"reference_code": "MIXED001",
				"display_name": "Mixed Calculation",
				"data_source": "Calculated Amount",
				"calculation_formula": "(API001 + ACC001) * 0.5",
			},
			{
				"reference_code": "FINAL001",
				"display_name": "Final Result",
				"data_source": "Calculated Amount",
				"calculation_formula": "MIXED001 + API001",
			},
		]

		test_template = FinancialReportTemplateTestCase.create_test_template_with_rows(test_rows)
		resolver = DependencyResolver(test_template)
		order = resolver.get_processing_order()
		positions = {row.reference_code: i for i, row in enumerate(order)}

		# API rows should be processed first
		self.assertLess(positions["API001"], positions["ACC001"])
		self.assertLess(positions["API001"], positions["MIXED001"])

		# Account data should be processed before formula rows
		self.assertLess(positions["ACC001"], positions["MIXED001"])

		# Mixed calculation should be processed before final result
		self.assertLess(positions["MIXED001"], positions["FINAL001"])

		# Verify dependencies
		self.assertEqual(set(resolver.dependencies["MIXED001"]), {"API001", "ACC001"})
		self.assertEqual(set(resolver.dependencies["FINAL001"]), {"MIXED001", "API001"})

	# 4. FORMULA PARSING
	def test_extract_from_complex_formulas(self):
		test_rows = [
			{
				"reference_code": "INCOME",
				"display_name": "Total Income",
				"data_source": "Account Data",
				"balance_type": "Closing Balance",
				"calculation_formula": '["root_type", "=", "Income"]',
			},
			{
				"reference_code": "EXPENSE",
				"display_name": "Total Expense",
				"data_source": "Account Data",
				"balance_type": "Closing Balance",
				"calculation_formula": '["root_type", "=", "Expense"]',
			},
			{
				"reference_code": "TAX_RATE",
				"display_name": "Tax Rate",
				"data_source": "Account Data",
				"balance_type": "Closing Balance",
				"calculation_formula": '["account_name", "like", "Tax"]',
			},
			{
				"reference_code": "NET_RESULT",
				"display_name": "Net Result",
				"data_source": "Calculated Amount",
				"calculation_formula": "(INCOME - EXPENSE) * (1 - TAX_RATE / 100)",
			},
		]

		test_template = FinancialReportTemplateTestCase.create_test_template_with_rows(test_rows)
		resolver = DependencyResolver(test_template)

		# Should correctly identify all three dependencies in complex formula
		net_deps = resolver.dependencies.get("NET_RESULT", [])
		self.assertEqual(set(net_deps), {"INCOME", "EXPENSE", "TAX_RATE"})

	def test_extract_with_math_functions(self):
		test_rows = [
			{
				"reference_code": "INCOME",
				"display_name": "Total Income",
				"data_source": "Account Data",
				"balance_type": "Closing Balance",
				"calculation_formula": '["root_type", "=", "Income"]',
			},
			{
				"reference_code": "EXPENSE",
				"display_name": "Total Expense",
				"data_source": "Account Data",
				"balance_type": "Closing Balance",
				"calculation_formula": '["root_type", "=", "Expense"]',
			},
			{
				"reference_code": "TAX",
				"display_name": "Tax Amount",
				"data_source": "Account Data",
				"balance_type": "Closing Balance",
				"calculation_formula": '["account_name", "like", "Tax"]',
			},
			{
				"reference_code": "MATH_TEST1",
				"display_name": "Mathematical Test 1",
				"data_source": "Calculated Amount",
				"calculation_formula": "max(INCOME, EXPENSE) + min(TAX, 0)",
			},
			{
				"reference_code": "MATH_TEST2",
				"display_name": "Mathematical Test 2",
				"data_source": "Calculated Amount",
				"calculation_formula": "abs(INCOME - EXPENSE) + round(TAX, 2)",
			},
			{
				"reference_code": "MATH_TEST3",
				"display_name": "Mathematical Test 3",
				"data_source": "Calculated Amount",
				"calculation_formula": "sqrt(pow(INCOME, 2) + pow(EXPENSE, 2))",
			},
		]

		test_template = FinancialReportTemplateTestCase.create_test_template_with_rows(test_rows)
		resolver = DependencyResolver(test_template)

		# MATH_TEST1 should correctly identify dependencies despite max/min functions
		self.assertEqual(set(resolver.dependencies["MATH_TEST1"]), {"INCOME", "EXPENSE", "TAX"})

		# MATH_TEST2 should correctly identify dependencies despite abs/round functions
		self.assertEqual(set(resolver.dependencies["MATH_TEST2"]), {"INCOME", "EXPENSE", "TAX"})

		# MATH_TEST3 should correctly identify dependencies despite sqrt/pow functions
		self.assertEqual(set(resolver.dependencies["MATH_TEST3"]), {"INCOME", "EXPENSE"})

	def test_accurate_reference_extraction(self):
		test_rows = [
			{
				"reference_code": "INC001",
				"display_name": "Income Base",
				"data_source": "Account Data",
				"calculation_formula": '["account_type", "=", "Income"]',
				"balance_type": "Closing Balance",
			},
			{
				"reference_code": "INC002",
				"display_name": "Income Secondary",
				"data_source": "Account Data",
				"calculation_formula": '["account_type", "=", "Income"]',
				"balance_type": "Closing Balance",
			},
			{
				"reference_code": "INC001_2023",  # Should not match INC001
				"display_name": "Income 2023",
				"data_source": "Account Data",
				"calculation_formula": '["account_type", "=", "Income"]',
				"balance_type": "Closing Balance",
			},
			{
				"reference_code": "TEST1",
				"display_name": "Test Formula 1",
				"data_source": "Calculated Amount",
				"calculation_formula": "2 * INC001",  # Should correctly extract INC001
			},
			{
				"reference_code": "TEST2",
				"display_name": "Test Formula 2",
				"data_source": "Calculated Amount",
				"calculation_formula": "INC001 + INC002",  # Word boundaries require separation
			},
			{
				"reference_code": "TEST3",
				"display_name": "Test Formula 3",
				"data_source": "Calculated Amount",
				"calculation_formula": "INC001_2023 + INC001",  # Should match both correctly
			},
			{
				"reference_code": "TEST4",
				"display_name": "Test Formula 4",
				"data_source": "Calculated Amount",
				"calculation_formula": "INC001_2023*INC001",  # No space separation but different tokens
			},
		]

		test_template = FinancialReportTemplateTestCase.create_test_template_with_rows(test_rows)
		resolver = DependencyResolver(test_template)

		# TEST1 should only depend on INC001
		self.assertEqual(resolver.dependencies["TEST1"], ["INC001"])

		# TEST2 should match both INC001 and INC002 (separated by space and +)
		self.assertEqual(set(resolver.dependencies["TEST2"]), {"INC001", "INC002"})

		# TEST3 should depend on both INC001_2023 and INC001
		self.assertEqual(set(resolver.dependencies["TEST3"]), {"INC001_2023", "INC001"})

		# TEST4 should depend on both INC001_2023 and INC001 (separated by *)
		self.assertEqual(set(resolver.dependencies["TEST4"]), {"INC001_2023", "INC001"})

	def test_prevent_partial_reference_matches(self):
		test_rows = [
			{
				"reference_code": "INC001",
				"display_name": "Income",
				"data_source": "Account Data",
				"calculation_formula": '["account_type", "=", "Income"]',
				"balance_type": "Closing Balance",
			},
			{
				"reference_code": "INC001_ADJ",  # Contains INC001 but shouldn't match
				"display_name": "Income Adjustment",
				"data_source": "Account Data",
				"calculation_formula": '["account_type", "=", "Income"]',
				"balance_type": "Closing Balance",
			},
			{
				"reference_code": "RESULT",
				"display_name": "Result",
				"data_source": "Calculated Amount",
				"calculation_formula": "INC001 + 500",  # Should only match INC001, not INC001_ADJ
			},
		]

		test_template = FinancialReportTemplateTestCase.create_test_template_with_rows(test_rows)
		resolver = DependencyResolver(test_template)

		# RESULT should only depend on INC001, not INC001_ADJ
		self.assertEqual(resolver.dependencies["RESULT"], ["INC001"])

		# Processing order should work correctly
		order = resolver.get_processing_order()
		positions = {row.reference_code: i for i, row in enumerate(order)}

		self.assertLess(positions["INC001"], positions["RESULT"])
		# INC001_ADJ can be processed in any order relative to RESULT since there's no dependency
		self.assertIn("INC001_ADJ", positions)

	# 5. EDGE CASES
	def test_rows_without_dependencies(self):
		test_rows = [
			{
				"reference_code": "A001",
				"display_name": "Account Row",
				"data_source": "Account Data",
				"balance_type": "Closing Balance",
				"calculation_formula": '["account_type", "=", "Income"]',
			},
			{
				"reference_code": "B001",
				"display_name": "Static Value",
				"data_source": "Calculated Amount",
				"calculation_formula": "1000 + 500",  # No reference codes
			},
		]

		test_template = FinancialReportTemplateTestCase.create_test_template_with_rows(test_rows)
		resolver = DependencyResolver(test_template)

		# B001 should have no dependencies
		self.assertEqual(resolver.dependencies.get("B001", []), [])

		# Should still process correctly
		order = resolver.get_processing_order()
		self.assertEqual(len(order), 2)

	def test_handle_empty_reference_codes(self):
		test_rows = [
			{
				"reference_code": "VALID001",
				"display_name": "Valid Row",
				"data_source": "Account Data",
				"balance_type": "Closing Balance",
				"calculation_formula": '["account_type", "=", "Income"]',
			},
			{
				"reference_code": "",  # Empty string
				"display_name": "Empty Reference",
				"data_source": "Account Data",
				"balance_type": "Closing Balance",
				"calculation_formula": '["account_type", "=", "Asset"]',
			},
			{
				"reference_code": "   ",  # Whitespace only
				"display_name": "Whitespace Reference",
				"data_source": "Account Data",
				"balance_type": "Closing Balance",
				"calculation_formula": '["account_type", "=", "Liability"]',
			},
			{
				"reference_code": None,  # None value
				"display_name": "None Reference",
				"data_source": "Account Data",
				"balance_type": "Closing Balance",
				"calculation_formula": '["account_type", "=", "Expense"]',
			},
			{
				"reference_code": "CALC001",
				"display_name": "Calculated Row",
				"data_source": "Calculated Amount",
				"calculation_formula": "VALID001 * 2",  # Should only depend on VALID001
			},
		]

		test_template = FinancialReportTemplateTestCase.create_test_template_with_rows(test_rows)
		resolver = DependencyResolver(test_template)

		# Should not break dependency resolution
		order = resolver.get_processing_order()
		self.assertEqual(len(order), 5)  # All rows should be present

		# CALC001 should only depend on VALID001
		self.assertEqual(resolver.dependencies.get("CALC001", []), ["VALID001"])

		# Verify processing order
		positions = {
			row.reference_code: i
			for i, row in enumerate(order)
			if row.reference_code and row.reference_code.strip()
		}
		self.assertLess(positions["VALID001"], positions["CALC001"])

	def test_include_orphaned_nodes(self):
		test_rows = [
			{
				"reference_code": "USED001",
				"display_name": "Used Row",
				"data_source": "Account Data",
				"balance_type": "Closing Balance",
				"calculation_formula": '["account_type", "=", "Income"]',
			},
			{
				"reference_code": "ORPHAN001",
				"display_name": "Orphaned Row 1",
				"data_source": "Account Data",
				"balance_type": "Closing Balance",
				"calculation_formula": '["account_type", "=", "Asset"]',
			},
			{
				"reference_code": "ORPHAN002",
				"display_name": "Orphaned Row 2",
				"data_source": "Account Data",
				"balance_type": "Closing Balance",
				"calculation_formula": '["account_type", "=", "Liability"]',
			},
			{
				"reference_code": "DEPENDENT",
				"display_name": "Dependent Row",
				"data_source": "Calculated Amount",
				"calculation_formula": "USED001 * 2",  # Only uses USED001
			},
		]

		test_template = FinancialReportTemplateTestCase.create_test_template_with_rows(test_rows)
		resolver = DependencyResolver(test_template)
		order = resolver.get_processing_order()

		# All rows should be included in processing order
		self.assertEqual(len(order), 4)

		positions = {row.reference_code: i for i, row in enumerate(order) if row.reference_code}

		# USED001 should be processed before DEPENDENT
		self.assertLess(positions["USED001"], positions["DEPENDENT"])

		# Orphaned rows should be included but have no dependencies
		self.assertIn("ORPHAN001", positions)
		self.assertIn("ORPHAN002", positions)

		# Orphaned rows should have no dependencies recorded
		self.assertEqual(resolver.dependencies.get("ORPHAN001", []), [])
		self.assertEqual(resolver.dependencies.get("ORPHAN002", []), [])

	def test_handle_valid_missing_references(self):
		test_rows = [
			{
				"reference_code": "A001",
				"display_name": "Row A",
				"data_source": "Account Data",
				"balance_type": "Closing Balance",
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
		test_template = FinancialReportTemplateTestCase.create_test_template_with_rows(test_rows)
		resolver = DependencyResolver(test_template)
		# Basic test - ensure it doesn't crash
		processing_order = resolver.get_processing_order()
		self.assertEqual(len(processing_order), 2)

	# 6. ERROR DETECTION
	def test_circular_dependency(self):
		"""Test detection of circular dependency (A -> B -> C -> A)"""
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
		test_template = FinancialReportTemplateTestCase.create_test_template_with_rows(test_rows)
		with self.assertRaises(frappe.ValidationError):
			DependencyResolver(test_template)
