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
	def test_resolve_basic_processing_order(self):
		resolver = DependencyResolver(self.test_template)
		order = resolver.get_processing_order()

		# Should process account rows before formula rows
		account_indices = [i for i, row in enumerate(order) if row.data_source == "Account Data"]
		formula_indices = [i for i, row in enumerate(order) if row.data_source == "Calculated Amount"]

		self.assertTrue(all(ai < fi for ai in account_indices for fi in formula_indices))

	def test_resolve_simple_dependency(self):
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
	def test_resolve_multiple_dependencies(self):
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

	def test_resolve_chain_dependencies(self):
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

	def test_resolve_diamond_dependency_pattern(self):
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

	def test_resolve_independent_formula_row_groups(self):
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
	def test_resolve_mixed_data_sources(self):
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

	def test_resolve_api_to_formula_dependencies(self):
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

	def test_resolve_cross_datasource_dependencies(self):
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

	def test_extract_references_with_math_functions(self):
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

	def test_extract_accurate_reference_matching(self):
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
	def test_resolve_rows_without_dependencies(self):
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

	def test_resolve_include_orphaned_nodes(self):
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
	def test_detect_circular_dependency(self):
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


class TestFormulaCalculator(FinancialReportTemplateTestCase):
	"""Test cases for FormulaCalculator class"""

	def _create_mock_report_row(self, formula: str, reference_code: str = "TEST_ROW"):
		class MockReportRow:
			def __init__(self, formula, ref_code):
				self.calculation_formula = formula
				self.reference_code = ref_code
				self.data_source = "Calculated Amount"
				self.idx = 1
				self.reverse_sign = 0

		return MockReportRow(formula, reference_code)

	# 1. FOUNDATION TESTS
	def test_evaluate_basic_operations(self):
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

		result = calculator.evaluate_formula(self._create_mock_report_row("INC001 - EXP001"))
		expected = [200.0, 300.0, 400.0]  # [1000-800, 1200-900, 1500-1100]
		self.assertEqual(result, expected)

		result = calculator.evaluate_formula(self._create_mock_report_row("INC001 * 2"))
		expected = [2000.0, 2400.0, 3000.0]
		self.assertEqual(result, expected)

		result = calculator.evaluate_formula(self._create_mock_report_row("INC001 / 10"))
		expected = [100.0, 120.0, 150.0]
		self.assertEqual(result, expected)

		result = calculator.evaluate_formula(self._create_mock_report_row("(INC001 - EXP001) * 0.8"))
		expected = [160.0, 240.0, 320.0]  # [(1000-800)*0.8, (1200-900)*0.8, (1500-1100)*0.8]
		self.assertEqual(result, expected)

		result = calculator.evaluate_formula(self._create_mock_report_row("abs(NEG_VAL)"))
		expected = [100.0, 200.0, 150.0]
		self.assertEqual(result, expected)

		result = calculator.evaluate_formula(self._create_mock_report_row("max(INC001, EXP001)"))
		expected = [1000.0, 1200.0, 1500.0]  # INC001 is always larger
		self.assertEqual(result, expected)

		result = calculator.evaluate_formula(self._create_mock_report_row("min(INC001, EXP001)"))
		expected = [800.0, 900.0, 1100.0]  # EXP001 is always smaller
		self.assertEqual(result, expected)

	def test_handle_division_by_zero(self):
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

		result = calculator.evaluate_formula(self._create_mock_report_row("NUMERATOR / ZERO_VAL"))
		expected = [0.0, 0.0, 0.0]
		self.assertEqual(result, expected)

	# 2. DATA HANDLING TESTS
	def test_handle_missing_values(self):
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

		result = calculator.evaluate_formula(self._create_mock_report_row("SHORT_DATA + NORMAL_DATA"))

		expected = [150.0, 260.0, 70.0]  # [100+50, 200+60, 0+70]
		self.assertEqual(result, expected)

		# Empty row_data
		empty_calculator = FormulaCalculator({}, period_list)
		result = empty_calculator.evaluate_formula(self._create_mock_report_row("MISSING_CODE * 2"))
		expected = [0.0, 0.0, 0.0]
		self.assertEqual(result, expected)

		# None values
		row_data_with_none = {
			"WITH_NONE": [100.0, None, 300.0],
			"NORMAL": [10.0, 20.0, 30.0],
		}
		none_calculator = FormulaCalculator(row_data_with_none, period_list)
		result = none_calculator.evaluate_formula(self._create_mock_report_row("WITH_NONE + NORMAL"))
		expected = [110.0, 20.0, 330.0]  # [100+10, 0+20, 300+30]
		self.assertEqual(result, expected)

		# Zero periods
		zero_period_calculator = FormulaCalculator({"TEST": [100.0]}, [])
		result = zero_period_calculator.evaluate_formula(self._create_mock_report_row("TEST * 2"))
		expected = []  # No periods means no results
		self.assertEqual(result, expected)

	def test_handle_invalid_reference_codes(self):
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
		result = calculator.evaluate_formula(self._create_mock_report_row("VALID_CODE * 2"))
		expected = [200.0, 400.0, 600.0]
		self.assertEqual(result, expected)

		# Test with invalid reference code - should return 0.0 (code won't be in context)
		result = calculator.evaluate_formula(self._create_mock_report_row("INVALID_CODE * 2"))
		expected = [0.0, 0.0, 0.0]
		self.assertEqual(result, expected)

		# Test reference code case sensitivity
		result = calculator.evaluate_formula(
			self._create_mock_report_row("valid_code * 2")
		)  # lowercase version
		expected = [0.0, 0.0, 0.0]  # Should fail since codes are case-sensitive
		self.assertEqual(result, expected)

	def test_handle_mismatched_period_data_lengths(self):
		"""Test scenarios with mismatched period data"""
		# Test when row_data has more values than periods
		row_data_extra = {
			"EXTRA_DATA": [100.0, 200.0, 300.0, 400.0, 500.0],  # 5 values
		}
		period_list_short = [
			{"key": "2023_q1", "from_date": "2023-01-01", "to_date": "2023-03-31"},
			{"key": "2023_q2", "from_date": "2023-04-01", "to_date": "2023-06-30"},
		]  # Only 2 periods

		calculator_extra = FormulaCalculator(row_data_extra, period_list_short)
		result = calculator_extra.evaluate_formula(self._create_mock_report_row("EXTRA_DATA * 2"))
		expected = [200.0, 400.0]  # Only processes first 2 values
		self.assertEqual(result, expected)

		# Test when all row data arrays have different lengths
		row_data_mixed = {
			"SHORT": [100.0],  # 1 value
			"MEDIUM": [200.0, 300.0],  # 2 values
			"LONG": [400.0, 500.0, 600.0],  # 3 values
		}
		period_list_three = [
			{"key": "2023_q1", "from_date": "2023-01-01", "to_date": "2023-03-31"},
			{"key": "2023_q2", "from_date": "2023-04-01", "to_date": "2023-06-30"},
			{"key": "2023_q3", "from_date": "2023-07-01", "to_date": "2023-09-30"},
		]

		calculator_mixed = FormulaCalculator(row_data_mixed, period_list_three)
		result = calculator_mixed.evaluate_formula(self._create_mock_report_row("SHORT + MEDIUM + LONG"))
		# Period 0: 100 + 200 + 400 = 700
		# Period 1: 0 + 300 + 500 = 800
		# Period 2: 0 + 0 + 600 = 600
		expected = [700.0, 800.0, 600.0]
		self.assertEqual(result, expected)

	# 3. COMPLEX EXPRESSIONS
	def test_evaluate_complex_expressions(self):
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

		result = calculator.evaluate_formula(
			self._create_mock_report_row("(REVENUE - COST) * (1 - TAX_RATE)")
		)
		expected = [
			(10000 - 6000) * (1 - 0.25),
			(12000 - 7200) * (1 - 0.25),
			(15000 - 9000) * (1 - 0.30),
		]
		self.assertEqual(result, expected)

		result = calculator.evaluate_formula(self._create_mock_report_row("round(REVENUE / COST, 2)"))
		expected = [
			round(10000 / 6000, 2),
			round(12000 / 7200, 2),
			round(15000 / 9000, 2),
		]
		self.assertEqual(result, expected)

		result = calculator.evaluate_formula(
			self._create_mock_report_row("REVENUE + COST * TAX_RATE - 100")
		)  # Tests PEMDAS order
		expected = [
			10000 + 6000 * 0.25 - 100,
			12000 + 7200 * 0.25 - 100,
			15000 + 9000 * 0.30 - 100,
		]
		self.assertEqual(result, expected)

		result = calculator.evaluate_formula(
			self._create_mock_report_row("((REVENUE + COST) * (TAX_RATE + 0.1)) / 2")
		)
		expected = [
			((10000 + 6000) * (0.25 + 0.1)) / 2,
			((12000 + 7200) * (0.25 + 0.1)) / 2,
			((15000 + 9000) * (0.30 + 0.1)) / 2,
		]
		self.assertEqual(result, expected)

		result = calculator.evaluate_formula(self._create_mock_report_row("REVENUE * 2.5 + 100"))
		expected = [
			10000 * 2.5 + 100,
			12000 * 2.5 + 100,
			15000 * 2.5 + 100,
		]
		self.assertEqual(result, expected)

	def test_evaluate_nested_function_combinations(self):
		row_data = {
			"BASE": [4.0],
			"POSITIVE": [16.0],  # Use positive number for sqrt
			"DECIMAL": [2.7],
		}
		period_list = [{"key": "2023_q1", "from_date": "2023-01-01", "to_date": "2023-03-31"}]

		calculator = FormulaCalculator(row_data, period_list)

		result = calculator.evaluate_formula(self._create_mock_report_row("round(sqrt(POSITIVE), 2)"))
		expected = round((16.0**0.5), 2)  # round(sqrt(16), 2) = round(4.0, 2) = 4.0
		self.assertEqual(result[0], expected)

		result = calculator.evaluate_formula(
			self._create_mock_report_row("max(POSITIVE, min(BASE, DECIMAL))")
		)
		expected = max(16.0, min(4.0, 2.7))  # max(16.0, 2.7) = 16.0
		self.assertEqual(result[0], expected)

		result = calculator.evaluate_formula(
			self._create_mock_report_row("pow(max(BASE, 2), min(DECIMAL, 3))")
		)
		expected = pow(max(4.0, 2), min(2.7, 3))  # pow(4.0, 2.7)
		self.assertAlmostEqual(result[0], expected, places=2)

	# 4. FINANCIAL DOMAIN
	def test_calculate_financial_use_cases(self):
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

		# Best quarterly performance
		result = calculator.evaluate_formula(self._create_mock_report_row("max(REVENUE_Q1, REVENUE_Q2)"))
		self.assertEqual(result[0], 1200000.0)

		# Absolute variance (remove negative sign for reporting)
		result = calculator.evaluate_formula(self._create_mock_report_row("abs(BUDGET_VARIANCE)"))
		self.assertEqual(result[0], 50000.0)

		# Rounded reporting figures
		result = calculator.evaluate_formula(self._create_mock_report_row("round(ACTUAL_COSTS)"))
		self.assertEqual(result[0], 123457.0)  # Rounded to nearest whole number

		# Conservative estimates
		result = calculator.evaluate_formula(self._create_mock_report_row("floor(ACTUAL_COSTS / 1000)"))
		self.assertEqual(result[0], 123.0)  # Conservative thousands

		# Compound growth calculations
		result = calculator.evaluate_formula(self._create_mock_report_row("pow(GROWTH_RATE, YEARS)"))
		expected = flt(1.15**5, get_currency_precision())
		self.assertEqual(result[0], expected)

		# Profit calculation with rounding
		result = calculator.evaluate_formula(
			self._create_mock_report_row("round((REVENUE_Q1 - EXPENSES) / REVENUE_Q1 * 100)")
		)
		self.assertEqual(result[0], 20.0)  # 20% profit margin

	def test_calculate_common_financial_patterns(self):
		"""Test patterns commonly used in financial calculations"""
		row_data = {
			"ACTUAL": [100000.0],
			"BUDGET": [80000.0],
			"PREVIOUS_YEAR": [90000.0],
			"LOWER_BOUND": [50000.0],
			"UPPER_BOUND": [150000.0],
		}
		period_list = [{"key": "2023_q1", "from_date": "2023-01-01", "to_date": "2023-03-31"}]

		calculator = FormulaCalculator(row_data, period_list)

		result = calculator.evaluate_formula(
			self._create_mock_report_row("(ACTUAL - BUDGET) / (BUDGET + 0.0001) * 100")
		)
		expected = (100000.0 - 80000.0) / (80000.0 + 0.0001) * 100
		self.assertAlmostEqual(result[0], expected, places=2)

		# conditional logic simulation: max(0, ACTUAL - BUDGET) (similar to IF positive)
		result = calculator.evaluate_formula(self._create_mock_report_row("max(0, ACTUAL - BUDGET)"))
		expected = max(0, 100000.0 - 80000.0)  # 20000.0
		self.assertEqual(result[0], expected)

		# clamping patterns: min(max(ACTUAL, LOWER_BOUND), UPPER_BOUND)
		result = calculator.evaluate_formula(
			self._create_mock_report_row("min(max(ACTUAL, LOWER_BOUND), UPPER_BOUND)")
		)
		expected = min(max(100000.0, 50000.0), 150000.0)  # min(100000.0, 150000.0) = 100000.0
		self.assertEqual(result[0], expected)

		# year-over-year growth calculation
		result = calculator.evaluate_formula(
			self._create_mock_report_row("(ACTUAL - PREVIOUS_YEAR) / PREVIOUS_YEAR * 100")
		)
		expected = (100000.0 - 90000.0) / 90000.0 * 100
		self.assertAlmostEqual(result[0], expected, places=2)

	# 5. EDGE CASES
	def test_handle_error_cases(self):
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
		result = calculator.evaluate_formula(self._create_mock_report_row("NORMAL + +"))  # Invalid syntax
		expected = [0.0, 0.0, 0.0]
		self.assertEqual(result, expected)

		# Test undefined variable - should return 0.0 for all periods
		result = calculator.evaluate_formula(self._create_mock_report_row("UNDEFINED_VAR * 2"))
		expected = [0.0, 0.0, 0.0]
		self.assertEqual(result, expected)

		# Test empty formula - should return 0.0 for all periods
		result = calculator.evaluate_formula(self._create_mock_report_row(""))
		expected = [0.0, 0.0, 0.0]
		self.assertEqual(result, expected)

		# Test whitespace and formatting tolerance
		result = calculator.evaluate_formula(
			self._create_mock_report_row("  NORMAL   +   100  ")
		)  # Extra spaces
		expected = [200.0, 300.0, 400.0]
		self.assertEqual(result, expected)

		# Test extremely long formulas
		long_formula = "NORMAL + " + " + ".join(["10"] * 100)  # Very long formula
		result = calculator.evaluate_formula(self._create_mock_report_row(long_formula))
		expected = [1100.0, 1200.0, 1300.0]  # 100 + (100 * 10) = 1100 added to each value
		self.assertEqual(result, expected)

		# Test Unicode characters in formula (should fail gracefully)
		result = calculator.evaluate_formula(
			self._create_mock_report_row("NORMAL + ∞")
		)  # Unicode infinity symbol
		expected = [0.0, 0.0, 0.0]
		self.assertEqual(result, expected)

	def test_evaluate_math_function_edge_cases(self):
		"""Test edge cases for mathematical functions"""
		row_data = {
			"ZERO": [0.0],
			"SMALL_DECIMAL": [0.0001],
		}
		period_list = [{"key": "2023_q1", "from_date": "2023-01-01", "to_date": "2023-03-31"}]

		calculator = FormulaCalculator(row_data, period_list)

		# Test sqrt with zero values
		result = calculator.evaluate_formula(self._create_mock_report_row("sqrt(ZERO)"))
		self.assertEqual(result[0], 0.0)

		# Test very small numbers precision
		result = calculator.evaluate_formula(self._create_mock_report_row("SMALL_DECIMAL * SMALL_DECIMAL"))
		expected = 0.0001 * 0.0001
		# Depends on currency precision
		self.assertTrue(result[0] == 0.0 or abs(result[0] - expected) < 1e-6)

	# 6. OTHER
	def test_prevent_security_vulnerabilities(self):
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
				result = calculator.evaluate_formula(self._create_mock_report_row(expr))
				self.assertEqual(result, [0.0], f"Harmful expression '{expr}' should return [0.0]")

		# Only safe mathematical operations work
		safe_expressions = [
			"TEST_VAL + 50",
			"abs(TEST_VAL - 200)",
			"min(TEST_VAL, 50)",
			"max(TEST_VAL, 150)",
			"round(TEST_VAL / 3, 2)",
		]

		for expr in safe_expressions:
			with self.subTest(expression=expr):
				result = calculator.evaluate_formula(self._create_mock_report_row(expr))
				self.assertNotEqual(result, [0.0], f"Safe expression '{expr}' should not return [0.0]")
				self.assertIsInstance(result[0], float, f"Safe expression '{expr}' should return a float")

	def test_build_context_validation(self):
		row_data = {
			"TEST1": [100.0, 200.0, 300.0],
			"TEST2": [10.0, 20.0, 30.0],
		}
		period_list = [
			{"key": "2023_q1", "from_date": "2023-01-01", "to_date": "2023-03-31"},
			{"key": "2023_q2", "from_date": "2023-04-01", "to_date": "2023-06-30"},
			{"key": "2023_q3", "from_date": "2023-07-01", "to_date": "2023-09-30"},
		]

		calculator = FormulaCalculator(row_data, period_list)

		# Test that context for each period contains the correct values
		context_0 = calculator._build_context(0)
		self.assertEqual(context_0["TEST1"], 100.0)
		self.assertEqual(context_0["TEST2"], 10.0)

		context_1 = calculator._build_context(1)
		self.assertEqual(context_1["TEST1"], 200.0)
		self.assertEqual(context_1["TEST2"], 20.0)

		context_2 = calculator._build_context(2)
		self.assertEqual(context_2["TEST1"], 300.0)
		self.assertEqual(context_2["TEST2"], 30.0)

		# Verify all expected math functions are available in context
		math_functions = ["abs", "round", "min", "max", "sum", "sqrt", "pow", "ceil", "floor"]
		for func_name in math_functions:
			self.assertIn(func_name, context_0)
			self.assertTrue(callable(context_0[func_name]))


class TestFilterExpressionParser(FinancialReportTemplateTestCase):
	"""Test cases for FilterExpressionParser class"""

	def _create_mock_report_row(self, formula: str, reference_code: str = "TEST_ROW"):
		class MockReportRow:
			def __init__(self, formula, ref_code):
				self.calculation_formula = formula
				self.reference_code = ref_code
				self.data_source = "Account Data"
				self.idx = 1
				self.reverse_sign = 0

		return MockReportRow(formula, reference_code)

	# 1. BASIC PARSING
	def test_parse_simple_equality_condition(self):
		parser = FilterExpressionParser()

		# Test simple equality condition
		simple_formula = '["account_type", "=", "Income"]'

		# Test with mock table
		from frappe.query_builder import DocType

		account_table = DocType("Account")
		mock_row = self._create_mock_report_row(simple_formula)
		condition = parser.build_condition(mock_row, account_table)
		self.assertIsNotNone(condition)

		# Verify the condition contains the expected field and value
		condition_str = str(condition)
		self.assertIn("account_type", condition_str)
		self.assertIn("Income", condition_str)

	def test_parse_logical_and_or_conditions(self):
		parser = FilterExpressionParser()
		from frappe.query_builder import DocType

		account_table = DocType("Account")

		# Test AND condition
		and_formula = """{"and": [["account_type", "=", "Income"], ["is_group", "=", 0]]}"""
		mock_row_and = self._create_mock_report_row(and_formula)
		condition = parser.build_condition(mock_row_and, account_table)
		self.assertIsNotNone(condition)

		condition_str = str(condition)
		self.assertIn("account_type", condition_str)
		self.assertIn("is_group", condition_str)
		self.assertIn("AND", condition_str)

		# Test OR condition
		or_formula = """{"or": [["root_type", "=", "Asset"], ["root_type", "=", "Liability"]]}"""
		mock_row_or = self._create_mock_report_row(or_formula)
		condition = parser.build_condition(mock_row_or, account_table)
		self.assertIsNotNone(condition)

		condition_str = str(condition)
		self.assertIn("root_type", condition_str)
		self.assertIn("Asset", condition_str)
		self.assertIn("Liability", condition_str)
		self.assertIn("OR", condition_str)

	# 2. OPERATOR SUPPORT
	def test_parse_valid_operators(self):
		parser = FilterExpressionParser()
		from frappe.query_builder import DocType

		account_table = DocType("Account")

		test_cases = [
			('["account_name", "!=", "Cash"]', "!="),
			('["account_number", "like", "1000"]', "like"),
			('["account_type", "in", ["Income", "Expense"]]', "in"),
			('["account_type", "not in", ["Asset", "Liability"]]', "not in"),
			('["account_name", "not like", "Expense"]', "not like"),
			('["account_number", ">=", 1000]', ">="),
			('["account_number", ">", 0]', ">"),
			('["account_number", "<=", 5000]', "<="),
			('["account_number", "<", 100]', "<"),
			('["is_group", "=", 0]', "="),
		]

		for formula, expected_op in test_cases:
			mock_row = self._create_mock_report_row(formula)
			condition = parser.build_condition(mock_row, account_table)
			self.assertIsNotNone(condition, f"Failed to build condition for operator {expected_op}")

	def test_build_logical_condition_with_reduce(self):
		parser = FilterExpressionParser()
		from frappe.query_builder import DocType

		account_table = DocType("Account")

		# Test AND logic with multiple conditions
		and_formula = '{"and": [["account_type", "=", "Income"], ["is_group", "=", 0], ["disabled", "=", 0]]}'
		mock_row_and = self._create_mock_report_row(and_formula)
		condition = parser.build_condition(mock_row_and, account_table)
		self.assertIsNotNone(condition)
		condition_str = str(condition)
		self.assertEqual(condition_str.count("AND"), 2)

		# Test OR logic with multiple conditions
		or_formula = '{"or": [["root_type", "=", "Asset"], ["root_type", "=", "Liability"], ["root_type", "=", "Income"]]}'
		mock_row_or = self._create_mock_report_row(or_formula)
		condition = parser.build_condition(mock_row_or, account_table)
		self.assertIsNotNone(condition)
		condition_str = str(condition)
		self.assertEqual(condition_str.count("OR"), 2)

	def test_operator_value_compatibility(self):
		parser = FilterExpressionParser()
		from frappe.query_builder import DocType

		account_table = DocType("Account")

		# Test "in" operator with list value - should work
		in_formula = '["account_type", "in", ["Income", "Expense"]]'
		mock_row_in = self._create_mock_report_row(in_formula)
		condition = parser.build_condition(mock_row_in, account_table)
		self.assertIsNotNone(condition)  # Should work with list

		# Test numeric operators with proper values
		numeric_formulas = [
			'["tax_rate", ">", 10.0]',
			'["tax_rate", ">=", 0]',
			'["tax_rate", "<", 50.0]',
			'["tax_rate", "<=", 100.0]',
		]

		for formula in numeric_formulas:
			mock_row = self._create_mock_report_row(formula)
			condition = parser.build_condition(mock_row, account_table)
			self.assertIsNotNone(condition)

	# 3. COMPLEX STRUCTURES
	def test_parse_complex_nested_filters(self):
		"""Test complex nested filter expressions"""
		parser = FilterExpressionParser()
		from frappe.query_builder import DocType

		account_table = DocType("Account")

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

		mock_row_complex = self._create_mock_report_row(complex_formula)
		condition = parser.build_condition(mock_row_complex, account_table)
		self.assertIsNotNone(condition)

		condition_str = str(condition)
		self.assertIn("root_type", condition_str)
		self.assertIn("account_category", condition_str)
		self.assertIn("is_group", condition_str)
		self.assertIn("AND", condition_str)
		self.assertIn("OR", condition_str)

	def test_parse_deeply_nested_conditions(self):
		parser = FilterExpressionParser()
		from frappe.query_builder import DocType

		account_table = DocType("Account")

		# Triple nesting: AND containing OR containing AND
		deep_nested = """{
            "and": [
                {
                    "or": [
                        {
                            "and": [
                                ["account_type", "=", "Income Account"],
                                ["is_group", "=", 0]
                            ]
                        },
                        ["root_type", "=", "Asset"]
                    ]
                },
                ["disabled", "=", 0]
            ]
        }"""

		mock_row_deep = self._create_mock_report_row(deep_nested)
		condition = parser.build_condition(mock_row_deep, account_table)
		self.assertIsNotNone(condition)

		condition_str = str(condition)
		self.assertIn("account_type", condition_str)
		self.assertIn("root_type", condition_str)
		self.assertIn("disabled", condition_str)
		self.assertIn("AND", condition_str)
		self.assertIn("OR", condition_str)

	# 4. VALUE TYPES
	def test_parse_different_value_types(self):
		"""Test different value types in conditions"""
		parser = FilterExpressionParser()
		from frappe.query_builder import DocType

		account_table = DocType("Account")

		test_cases = [
			'["tax_rate", ">=", 10.50]',  # Float
			'["is_group", "=", 1]',  # Integer
			'["account_name", "=", ""]',  # Empty string
			'["account_type", "in", ["Income Account", "Expense Account"]]',  # List value
		]

		for formula in test_cases:
			mock_row = self._create_mock_report_row(formula)
			condition = parser.build_condition(mock_row, account_table)
			self.assertIsNotNone(condition, f"Failed to build condition for {formula}")

	# 5. EDGE CASES
	def test_parse_special_characters_in_values(self):
		"""Test special characters in filter values"""
		parser = FilterExpressionParser()
		from frappe.query_builder import DocType

		account_table = DocType("Account")

		test_cases = [
			('["account_name", "=", "John\'s Account"]', "apostrophe"),
			('["account_number", "like", "%100%"]', "wildcards"),
			('["account_name", "=", "Test & Development"]', "ampersand"),
		]

		for formula, _case_type in test_cases:
			mock_row = self._create_mock_report_row(formula)
			condition = parser.build_condition(mock_row, account_table)
			self.assertIsNotNone(condition, f"Failed to build condition for {_case_type} case")

	def test_parse_logical_operator_edge_cases(self):
		"""Test edge cases for logical operators"""
		parser = FilterExpressionParser()
		from frappe.query_builder import DocType

		account_table = DocType("Account")

		# Test empty conditions list - should return None
		empty_and = '{"and": []}'
		mock_row_empty = self._create_mock_report_row(empty_and)
		condition = parser.build_condition(mock_row_empty, account_table)
		self.assertIsNone(condition)

		# Test single condition in logical operator
		single_condition = '{"and": [["account_type", "=", "Bank"]]}'
		mock_row_single = self._create_mock_report_row(single_condition)
		condition = parser.build_condition(mock_row_single, account_table)
		self.assertIsNotNone(condition)

		# Test case sensitivity - should be invalid
		wrong_case = '{"AND": [["account_type", "=", "Bank"]]}'
		mock_row_wrong = self._create_mock_report_row(wrong_case)
		condition = parser.build_condition(mock_row_wrong, account_table)
		self.assertIsNone(condition)  # Should return None due to invalid logical operator

	def test_build_condition_accepts_document_instance(self):
		parser = FilterExpressionParser()
		account_table = frappe.qb.DocType("Account")
		row_obj = frappe._dict(
			{
				"doctype": "Financial Report Row",
				"reference_code": "DOCROW1",
				"display_name": "Doc Row",
				"data_source": "Account Data",
				"balance_type": "Closing Balance",
				"calculation_formula": '["account_type", "=", "Income"]',
			}
		)

		# Unsaved child doc is sufficient for validation
		row_doc = frappe.get_doc(row_obj)
		cond = parser.build_condition(row_doc, account_table)
		self.assertIsNotNone(cond)

		# Also accepts plain frappe._dict object
		cond = parser.build_condition(row_obj, account_table)
		self.assertIsNotNone(cond)

	# 6. ERROR HANDLING
	def test_parse_invalid_filter_expressions(self):
		"""Test handling of invalid filter expressions"""
		parser = FilterExpressionParser()
		from frappe.query_builder import DocType

		account_table = DocType("Account")

		# Test malformed expressions - all should return None
		invalid_expressions = [
			'["incomplete"]',  # Missing operator and value
			'{"invalid": "structure"}',  # Wrong structure
			"not_a_list_or_dict",  # Invalid format
			'["field", "=", "value", "extra"]',  # Too many elements - actually might work due to slicing
			'["field"]',  # Single element
			'["field", "="]',  # Missing value - actually gets handled as empty value
			'{"AND": [["field", "=", "value"]]}',  # Wrong case
			'{"and": [["field", "=", "value"]], "or": [["field2", "=", "value2"]]}',  # Multiple keys
			'{"xor": [["field", "=", "value"]]}',  # Invalid logical operator
			'{"and": "not_a_list"}',  # Non-list value for logical operator
			"not even close to valid syntax",  # Unparseable string
		]

		for expr in invalid_expressions:
			mock_row = self._create_mock_report_row(expr)
			condition = parser.build_condition(mock_row, account_table)
			self.assertIsNone(condition, f"Expression {expr} should be invalid and return None")

	def test_parse_malformed_logical_conditions(self):
		"""Test malformed logical conditions"""
		parser = FilterExpressionParser()
		from frappe.query_builder import DocType

		account_table = DocType("Account")

		malformed_expressions = [
			'{"and": [["field", "=", "value"]], "or": [["field2", "=", "value2"]]}',  # Multiple keys
			'{"xor": [["field", "=", "value"]]}',  # Invalid logical operator
			'{"and": "not_a_list"}',  # Non-list value for logical operator
		]

		for expr in malformed_expressions:
			mock_row = self._create_mock_report_row(expr)
			condition = parser.build_condition(mock_row, account_table)
			self.assertIsNone(condition, f"Malformed expression {expr} should return None")

		# Test mixed types in conditions - should return None due to validation failure
		mixed_types = '{"and": [["account_type", "=", "Bank"], "string", 123]}'
		mock_row_mixed = self._create_mock_report_row(mixed_types)
		condition = parser.build_condition(mock_row_mixed, account_table)
		# Should return None because invalid sub-conditions cause validation to fail
		self.assertIsNone(condition)

	def test_handle_exception_robustness(self):
		"""Test exception handling for various inputs"""
		parser = FilterExpressionParser()
		from frappe.query_builder import DocType

		account_table = DocType("Account")

		problematic_inputs = [
			"not even close to valid syntax",  # Unparseable string
			'{"field": "value"}',  # JSON-like but not proper format
		]

		for test_input in problematic_inputs:
			mock_row = self._create_mock_report_row(test_input)
			condition = parser.build_condition(mock_row, account_table)
			self.assertIsNone(condition, f"Input {test_input} should result in None")

	# 7. BUILD CONDITIONS
	def test_build_condition_field_validation(self):
		"""Test field validation behavior"""
		parser = FilterExpressionParser()
		from frappe.query_builder import DocType

		account_table = DocType("Account")

		# Test with existing field - should work
		valid_formula = '["account_name", "=", "test"]'
		mock_row_valid = self._create_mock_report_row(valid_formula)
		condition = parser.build_condition(mock_row_valid, account_table)
		self.assertIsNotNone(condition)

		# Test with invalid formula - should return None
		invalid_formula = "invalid formula"
		mock_row_invalid = self._create_mock_report_row(invalid_formula)
		condition = parser.build_condition(mock_row_invalid, account_table)
		self.assertIsNone(condition)
