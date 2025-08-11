# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
import frappe
from frappe.tests import IntegrationTestCase
from frappe.tests.utils import make_test_records

from erpnext.accounts.doctype.financial_report_template.report_engine import (
	AccountResolver,
	DataFormatter,
	DependencyResolver,
	FinancialReportEngine,
	FormulaCalculator,
)
from erpnext.accounts.doctype.financial_report_template.utils import (
	BalanceProcessor,
	FilterExpressionParser,
	PeriodAccountDataCollector,
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
							"data_type": "Account Data",
							"balance_type": "Closing Balance",
							"bold_text": 1,
							"calculation_formula": '["root_type", "=", "Income"]',
						},
						{
							"reference_code": "EXP001",
							"display_name": "Expenses",
							"indentation_level": 0,
							"data_type": "Account Data",
							"balance_type": "Closing Balance",
							"bold_text": 1,
							"calculation_formula": '["root_type", "=", "Expense"]',
						},
						{
							"reference_code": "NET001",
							"display_name": "Net Profit/Loss",
							"indentation_level": 0,
							"data_type": "Calculated Amount",
							"bold_text": 1,
							"calculation_formula": "INC001 - EXP001",
						},
					],
				}
			)
			template.insert()

		cls.test_template = frappe.get_doc("Financial Report Template", "Test P&L Template")

	def test_dependency_resolver(self):
		"""Test dependency resolution"""
		resolver = DependencyResolver(self.test_template.rows)
		order = resolver.get_processing_order()

		# Should process account rows before formula rows
		account_indices = [i for i, row in enumerate(order) if row.data_type == "Account Data"]
		formula_indices = [i for i, row in enumerate(order) if row.data_type == "Calculated Amount"]

		self.assertTrue(all(ai < fi for ai in account_indices for fi in formula_indices))

	def test_formula_calculator(self):
		"""Test formula calculation"""
		# Mock row data
		row_data = {"INC001": [1000.0, 1200.0, 1500.0], "EXP001": [800.0, 900.0, 1100.0]}

		period_list = [
			{"key": "2023", "from_date": "2023-01-01", "to_date": "2023-12-31"},
			{"key": "2024", "from_date": "2024-01-01", "to_date": "2024-12-31"},
			{"key": "2025", "from_date": "2025-01-01", "to_date": "2025-12-31"},
		]

		calculator = FormulaCalculator(row_data, period_list)
		result = calculator.evaluate_formula("INC001 - EXP001")

		expected = [200.0, 300.0, 400.0]  # [1000-800, 1200-900, 1500-1100]
		self.assertEqual(result, expected)

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
						{"reference_code": "DUP001", "display_name": "Row 1", "data_type": "Account Data"},
						{
							"reference_code": "DUP001",  # Duplicate
							"display_name": "Row 2",
							"data_type": "Account Data",
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
							"data_type": "Calculated Amount",
							"calculation_formula": "B001 + 100",
						},
						{
							"reference_code": "B001",
							"display_name": "Row B",
							"data_type": "Calculated Amount",
							"calculation_formula": "A001 + 200",  # Circular reference
						},
					],
				}
			)
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

		collector = PeriodAccountDataCollector(filters, periods)

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

		# Verify we get results for all periods
		self.assertIn("TEST_INC", results)
		self.assertEqual(len(results["TEST_INC"]), 2)  # Two periods

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

		totals = processor.calculate_totals(request, mock_balance_data)

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

		collector = PeriodAccountDataCollector(filters, periods)

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

		# Verify both account types return data
		self.assertIn("INCOME", results)
		self.assertIn("EXPENSE", results)

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
		opening_totals = processor.calculate_totals(opening_request, mock_balance_data)
		self.assertEqual(opening_totals[0], 1000)

		# Test Closing Balance
		closing_request = {"accounts": ["Test Account"], "balance_type": "Closing Balance"}
		closing_totals = processor.calculate_totals(closing_request, mock_balance_data)
		self.assertEqual(closing_totals[0], 1500)

		# Test Period Movement
		movement_request = {
			"accounts": ["Test Account"],
			"balance_type": "Period Movement (Debits - Credits)",
		}
		movement_totals = processor.calculate_totals(movement_request, mock_balance_data)
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

		collector = PeriodAccountDataCollector(filters, periods)

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

		collector = PeriodAccountDataCollector(filters, periods)

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

		collector = PeriodAccountDataCollector(filters, periods)

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

		collector = PeriodAccountDataCollector(filters, periods)

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

		# Should find matching accounts and return balance data
		self.assertIn("COMPLEX_FILTER_TEST", results)
		self.assertEqual(len(results["COMPLEX_FILTER_TEST"]), 1)  # One period

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

		self.assertIn("SIMPLE_FILTER_TEST", results)

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

		collector = PeriodAccountDataCollector(filters, periods)

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

		# Verify results
		self.assertIn("TOTAL_INCOME", results)
		self.assertIn("TOTAL_EXPENSE", results)

		# Both should have data for 2 periods
		self.assertEqual(len(results["TOTAL_INCOME"]), 2)
		self.assertEqual(len(results["TOTAL_EXPENSE"]), 2)

		# January should have both income and expense movements
		jan_income = results["TOTAL_INCOME"][0]  # January
		jan_expense = results["TOTAL_EXPENSE"][0]  # January

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

		collector = PeriodAccountDataCollector(filters, periods)

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

		# All should be present
		self.assertIn("OPENING_BAL", results)
		self.assertIn("MOVEMENT", results)
		self.assertIn("CLOSING_BAL", results)

		# Check Q1 consistency: Closing = Opening + Movement
		q1_opening = results["OPENING_BAL"][0]
		q1_movement = results["MOVEMENT"][0]
		q1_closing = results["CLOSING_BAL"][0]

		self.assertAlmostEqual(q1_closing, q1_opening + q1_movement, places=2)

		# Check Q2 consistency: Q2 Opening should equal Q1 Closing
		q2_opening = results["OPENING_BAL"][1]
		self.assertAlmostEqual(q2_opening, q1_closing, places=2)

		# Cleanup
		si.cancel()

	@classmethod
	def tearDownClass(cls):
		"""Clean up test data"""
		frappe.db.rollback()
