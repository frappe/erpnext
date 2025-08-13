# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import ast
import re
from datetime import datetime
from functools import reduce
from typing import Any

import frappe
from frappe import _
from frappe.query_builder import Case
from frappe.query_builder.functions import Sum
from frappe.utils import cstr, date_diff, flt, getdate

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
	get_dimension_with_children,
)
from erpnext.accounts.doctype.financial_report_template.financial_report_template import (
	FinancialReportTemplate,
)
from erpnext.accounts.report.financial_statements import (
	get_columns,
	get_cost_centers_with_children,
	get_period_list,
)


class FinancialReportEngine:
	"""
	Main engine for processing custom financial report templates.
	Orchestrates the entire report generation process.
	"""

	def __init__(self, template_name: str, filters: dict[str, Any]):
		self.template_name = template_name
		self.filters = filters
		self.template = None
		self.period_list = []
		self.row_data = {}
		self.processed_rows = []

	def execute(self) -> tuple:
		try:
			self.load_template()

			self.generate_periods()

			columns = self.get_report_columns()

			self.process_rows()

			data = self.format_report_data()

			return columns, data

		except Exception as e:
			frappe.log_error(f"Financial Report Error: {e!s}")
			frappe.throw(_("Error generating financial report: {0}").format(str(e)))

	def load_template(self):
		self.template = frappe.get_doc("Financial Report Template", self.template_name)
		if not self.template:
			frappe.throw(_("Financial Report Template {0} not found").format(self.template_name))

		if self.template.disabled:
			frappe.throw(_("Financial Report Template {0} is disabled").format(self.template_name))

	def generate_periods(self):
		self.period_list = get_period_list(
			self.filters.from_fiscal_year,
			self.filters.to_fiscal_year,
			self.filters.period_start_date,
			self.filters.period_end_date,
			self.filters.filter_based_on,
			self.filters.periodicity,
			company=self.filters.company,
		)

	def get_report_columns(self) -> list[dict]:
		columns = [{"fieldname": "account", "label": _(""), "fieldtype": "Data", "width": 300}]

		period_columns = get_columns(
			self.filters.periodicity,
			self.period_list,
			self.filters.accumulated_values,
			self.filters.company,
		)

		columns.extend(period_columns)
		return columns

	def process_rows(self):
		"""Process all template rows in the correct dependency order"""
		processor = RowProcessor(self.template, self.filters, self.period_list)
		self.row_data = processor.process_all_rows()
		self.processed_rows = processor.get_processed_rows()

		# Store account details for potential use by frontend
		self.account_details = getattr(processor, "account_details", {})
		self.period_keys = getattr(processor, "period_keys", [])

	def format_report_data(self) -> list[dict]:
		"""Format the processed data for display"""
		formatter = DataFormatter(self.processed_rows, self.period_list)
		return formatter.format_for_display()


class RowProcessor:
	"""
	Processes individual rows of the financial report template.
	Handles dependency resolution and calculation order.
	"""

	def __init__(self, template, filters: dict, period_list: list):
		self.template = template
		self.filters = filters
		self.period_list = period_list
		self.row_data = {}
		self.processed_rows = []
		self.account_details = {}
		self.period_keys = []
		self.dependency_resolver = DependencyResolver(template)

	def process_all_rows(self) -> dict:
		processing_order = self.dependency_resolver.get_processing_order()

		account_rows = [row for row in processing_order if row.data_source == "Account Data"]
		if account_rows:
			collector = AccountDataCollector(self.filters, self.period_list)

			for row in account_rows:
				collector.add_data_request(row)

			account_data = collector.process_all_requests()

			# Store detailed account information for later use
			self.row_data.update(account_data.get("summary", {}))
			self.account_details = account_data.get("account_details", {})
			self.period_keys = account_data.get("period_keys", [])

		# Process remaining rows in order
		for row in processing_order:
			if row.data_source == "Account Data":
				self.process_account_row(row, self.row_data)
			elif row.data_source == "Calculated Amount":
				self.process_formula_row(row)
			elif row.data_source == "Blank Line":
				self.process_blank_row(row)

			self.processed_rows.append(row)

		return self.row_data

	def process_account_row(self, row, summary_data: dict):
		if not row.reference_code:
			return

		row._calculated_values = summary_data.get(row.reference_code, [0.0] * len(self.period_list))

	def process_formula_row(self, row):
		"""Process a formula calculation row"""
		calculator = FormulaCalculator(self.row_data, self.period_list)
		formula_result = calculator.evaluate_formula(row.calculation_formula)

		# Store in row_data and assign to row object
		if row.reference_code:
			self.row_data[row.reference_code] = formula_result

		# Always assign calculated values to the row object for display formatting
		row._calculated_values = formula_result

	def process_blank_row(self, row):
		return [""] * len(self.period_list)

	def get_processed_rows(self) -> list:
		"""Return the list of processed rows"""
		return self.processed_rows


class DependencyResolver:
	"""
	Resolves dependencies between rows to determine processing order.
	Ensures formulas are calculated after their dependencies.
	"""

	def __init__(self, template):
		self.template: FinancialReportTemplate = template
		self.rows = template.rows
		self.row_map = {row.reference_code: row for row in self.rows if row.reference_code}
		self.dependencies = {}
		self.analyze_dependencies()
		self.validate_dependencies()

	def analyze_dependencies(self):
		for row in self.rows:
			if not row.reference_code or not row.calculation_formula:
				continue

			if row.data_source == "Calculated Amount":
				deps = self.template._extract_reference_codes_from_formula(
					row.calculation_formula, self.row_map.keys()
				)
				self.dependencies[row.reference_code] = deps

	def validate_dependencies(self):
		if self.dependencies:
			self.check_circular_references(self.dependencies)

	def get_processing_order(self) -> list:
		# rows by type
		api_rows = []
		account_rows = []
		formula_rows = []
		other_rows = []

		for row in self.rows:
			if row.data_source == "Custom API":
				api_rows.append(row)
			elif row.data_source == "Account Data":
				account_rows.append(row)
			elif row.data_source == "Calculated Amount":
				formula_rows.append(row)
			else:
				other_rows.append(row)

		ordered_rows = api_rows + account_rows

		# sort formula rows
		if formula_rows:
			ordered_formula_rows = self.topological_sort(formula_rows)
			ordered_rows.extend(ordered_formula_rows)

		ordered_rows.extend(other_rows)

		return ordered_rows

	def topological_sort(self, formula_rows) -> list:
		formula_row_map = {row.reference_code: row for row in formula_rows if row.reference_code}

		# calculate in-degree
		in_degree = {code: 0 for code in formula_row_map.keys()}
		for code, deps in self.dependencies.items():
			if code in in_degree:
				for dep in deps:
					if dep in in_degree:  # only count dependencies within formula rows
						in_degree[code] += 1

		# initialize queue with nodes having no incoming edges
		queue = [code for code, degree in in_degree.items() if degree == 0]
		result = []

		while queue:
			current = queue.pop(0)
			if current in formula_row_map:
				result.append(formula_row_map[current])

			# reduce in-degree for dependent nodes
			for code, deps in self.dependencies.items():
				if current in deps and code in in_degree:
					in_degree[code] -= 1
					if in_degree[code] == 0:
						queue.append(code)

		# remaining formula rows
		for row in formula_rows:
			if not row.reference_code or row not in result:
				result.append(row)

		return result

	@staticmethod
	def check_circular_references(dependencies: dict[str, list[str]]):
		"""
		Efficient cycle detection using DFS (Depth-First Search) with three-color algorithm:
		- WHITE (0): unvisited node
		- GRAY (1): currently being processed (on recursion stack)
		- BLACK (2): fully processed

		Example cycle detection:
		A → B → C → A (cycle detected when A is GRAY and visited again)
		"""
		WHITE, GRAY, BLACK = 0, 1, 2
		colors = {node: WHITE for node in dependencies.keys()}

		def dfs(node, path):
			if colors[node] == GRAY:
				# Found a cycle - build cycle path for better error message
				cycle_start = path.index(node)
				cycle_nodes = [*path[cycle_start:], node]
				frappe.throw(_("Circular dependency detected: {0}").format(" → ".join(cycle_nodes)))

			if colors[node] == BLACK:
				return  # Already processed

			colors[node] = GRAY
			path.append(node)

			for neighbor in dependencies.get(node, []):
				if neighbor in colors:  # Only check dependencies that exist
					dfs(neighbor, path)

			path.pop()
			colors[node] = BLACK

		# Check all nodes
		for node in dependencies:
			if colors[node] == WHITE:
				dfs(node, [])


class AccountDataCollector:
	"""Collects account data across multiple periods efficiently."""

	def __init__(self, filters: dict[str, Any], periods: list[dict]):
		self.filters = filters
		self.periods = periods
		self.company = filters.get("company")
		self.data_requests = []

	def add_data_request(self, row, accounts: list[str] | None = None):
		if not accounts and row.calculation_formula:
			accounts = self.find_matching_accounts(row.calculation_formula)
		elif not accounts:
			accounts = []

		request = {
			"row": row,
			"accounts": accounts,
			"balance_type": row.balance_type,
			"reference_code": row.reference_code,
		}
		self.data_requests.append(request)

	def process_all_requests(self) -> dict[str, Any]:
		"""
		Process all data requests in a single optimized query.
		Steps: collect accounts → fetch balances → distribute results

		Returns:
		        dict: Contains both summary and detailed account data

		Example:
		        {
		                "summary": {
		                        "TOTAL_REVENUE": [15000.0, 18000.0, 22000.0],
		                        "TOTAL_EXPENSES": [12000.0, 14500.0, 16800.0],
		                        "NET_PROFIT": [3000.0, 3500.0, 5200.0]
		                },
		                "account_details": {
		                        "TOTAL_REVENUE": {
		                                "Sales - COMP": [10000.0, 12000.0, 15000.0],
		                                "Service Income - COMP": [5000.0, 6000.0, 7000.0]
		                        },
		                        "TOTAL_EXPENSES": {
		                                "Cost of Goods Sold - COMP": [8000.0, 9500.0, 11000.0],
		                                "Office Expenses - COMP": [4000.0, 5000.0, 5800.0]
		                        }
		                },
		                "period_keys": ["jan2024", "feb2024", "mar2024"]
		        }
		"""
		if not self.data_requests:
			return {"summary": {}, "account_details": {}, "period_keys": [p["key"] for p in self.periods]}

		all_accounts = set()
		for request in self.data_requests:
			all_accounts.update(request["accounts"])

		all_accounts = list(all_accounts)
		if not all_accounts:
			return {
				"summary": {
					req["reference_code"]: [0.0] * len(self.periods)
					for req in self.data_requests
					if req["reference_code"]
				},
				"account_details": {},
				"period_keys": [p["key"] for p in self.periods],
			}

		balance_processor = BalanceProcessor(self.filters, self.periods)
		account_balances = balance_processor.fetch_all_balances(all_accounts)

		# Build Summary
		account_details = {}
		summary_results = {}

		for request in self.data_requests:
			if reference_code := request["reference_code"]:
				# detailed
				account_values = balance_processor.get_account_values(request, account_balances)
				account_details[reference_code] = account_values

				# summary
				summary_results[reference_code] = balance_processor.calculate_totals(account_values)

		return {
			"summary": summary_results,
			"account_details": account_details,
			"period_keys": [p["key"] for p in self.periods],
		}

	def find_matching_accounts(self, filter_formula: str) -> list[str]:
		"""
		Find accounts matching filter criteria.

		Example:
		        Input: '["account_type", "=", "Cash"]'
		        Output: ["Cash - COMP", "Petty Cash - COMP", "Bank - COMP"]
		"""
		filter_parser = FilterExpressionParser()
		criteria = filter_parser.parse(filter_formula)

		account = frappe.qb.DocType("Account")
		query = frappe.qb.from_(account).select(account.name).where(account.disabled == 0)

		if self.company:
			query = query.where(account.company == self.company)

		where_condition = filter_parser.build_condition(criteria, account)
		if where_condition is not None:
			query = query.where(where_condition)

		query = query.orderby(account.name)
		result = query.run(as_dict=True)
		return [row.name for row in result]


class CustomAPIHandler:
	"""Handler for custom API data sources"""

	def __init__(self, filters, periods):
		self.filters = filters
		self.periods = periods
		self.cache = {}

	def execute_custom_api(self, row):
		"""Execute custom API with caching and error handling"""
		api_path = row.calculation_formula
		cache_key = f"{api_path}:{hash(frozenset(self.filters.items()))}"

		if cache_key in self.cache:
			return self.cache[cache_key]

		try:
			module_path, method_name = api_path.rsplit(".", 1)
			module = frappe.get_module(module_path)
			method = getattr(module, method_name)

			# Pass standardized context
			context = {
				"filters": self.filters,
				"periods": self.periods,
				"row": row,
				"company": self.filters.get("company"),
			}

			result = method(context)
			self.cache[cache_key] = result
			return result

		except Exception as e:
			frappe.log_error(f"Custom API Error: {api_path} - {e!s}")
			return [0.0] * len(self.periods)


class FormulaCalculator:
	"""
	Calculates formula expressions using row reference codes.
	Provides a secure evaluation environment using Frappe's safe_eval.
	"""

	def __init__(self, row_data: dict, period_list: list):
		self.row_data = row_data
		self.period_list = period_list

	def evaluate_formula(self, formula: str) -> list[float]:
		"""Evaluate a formula for all periods"""
		results = []

		for i, _period in enumerate(self.period_list):
			period_result = self.evaluate_formula_for_period(formula, i)
			results.append(period_result)

		return results

	def evaluate_formula_for_period(self, formula: str, period_index: int) -> float:
		"""Evaluate formula for a specific period"""
		try:
			# Build context with values for this period
			context = self.build_evaluation_context(period_index)

			# Use frappe's safe evaluation
			result = frappe.safe_eval(formula, eval_globals=None, eval_locals=context)
			return flt(result, 2)

		except ZeroDivisionError:
			frappe.log_error(f"Division by zero in formula: {formula}")
			return 0.0
		except Exception as e:
			frappe.log_error(f"Formula evaluation error: {formula} - {e!s}")
			return 0.0

	def build_evaluation_context(self, period_index: int) -> dict:
		"""Build safe evaluation context with row values"""
		context = {}

		for code, values in self.row_data.items():
			code: str
			if code and code.isidentifier():
				value = flt(values[period_index]) if len(values) > period_index else 0.0
				context[code] = value

			elif code:
				# Log warning about invalid reference code
				frappe.log_error(f"Invalid reference code format: {code}")

		# Add math functions using shared method
		context.update(self.get_math_functions())
		return context

	@staticmethod
	def get_math_functions() -> dict:
		"""Get safe mathematical functions for formula evaluation"""
		import math

		return {
			"abs": abs,
			"min": min,
			"max": max,
			"round": round,
			"sum": sum,
			# Add individual math functions for safety (not the full math module)
			"sqrt": math.sqrt,
			"pow": math.pow,
			"ceil": math.ceil,
			"floor": math.floor,
		}

	@classmethod
	def validate_formula_with_context(cls, formula: str, context: dict) -> tuple[bool, str | None]:
		"""
		Validate a formula with given context, returning success status and error message
		Used for validation purposes without needing a full FormulaCalculator instance
		"""
		try:
			# Add math functions to context
			validation_context = context.copy()
			validation_context.update(cls.get_math_functions())

			# Use frappe's safe_eval to validate formula
			result = frappe.safe_eval(formula, eval_globals=None, eval_locals=validation_context)

			# Ensure result is numeric
			if not isinstance(result, int | float):
				return f"Formula must return a numeric value, got: {type(result).__name__}"

			return None
		except Exception as e:
			return str(e)


class DataFormatter:
	"""
	Formats processed row data for display in the report.
	Handles indentation, styling, and visibility rules.
	"""

	def __init__(self, processed_rows: list, period_list: list):
		self.processed_rows = processed_rows
		self.period_list = period_list

	def format_for_display(self) -> list[dict]:
		"""Format all rows for display"""
		formatted_data = []

		for row in self.processed_rows:
			if self.should_show_row(row):
				formatted_row = self.format_single_row(row)
				formatted_data.append(formatted_row)

		return formatted_data

	def should_show_row(self, row) -> bool:
		"""Determine if a row should be shown based on visibility rules"""
		if row.hide_when_empty:
			# Check if all values are zero
			if hasattr(row, "_calculated_values"):
				return any(val != 0 for val in row._calculated_values)

		if row.hidden_calculation:
			return False

		return True

	def format_single_row(self, row) -> dict:
		"""Format a single row for display"""
		formatted_row = {
			"account": self.get_display_name(row),
			"indent": row.indentation_level or 0,
		}

		# Add period values
		if hasattr(row, "_calculated_values"):
			for i, period in enumerate(self.period_list):
				period_key = period.get("key", f"period_{i}")
				value = row._calculated_values[i] if i < len(row._calculated_values) else 0.0
				formatted_row[period_key] = flt(value, 2)

		# Apply formatting
		if row.bold_text:
			formatted_row["bold"] = 1
		if row.italic_text:
			formatted_row["italic"] = 1

		return formatted_row

	def get_display_name(self, row) -> str:
		"""Get the display name for a row with proper indentation"""
		indent = "   " * (row.indentation_level or 0)
		return f"{indent}{row.display_name or ''}"


class BalanceProcessor:
	def __init__(self, filters: dict, periods: list[dict]):
		self.filters = filters
		self.periods = periods
		self.company = filters.get("company")

	def fetch_all_balances(self, accounts: list[str]) -> dict:
		"""
		Fetch account balances for all periods with optimization.
		Steps: get opening balances → fetch GL entries → calculate running totals

		Returns:
		        dict: {account: {period_key: {opening, closing, movement}}}

		Example:
		        {
		                "Cash - COMP": {
		                        "jan2024": {"opening": 5000.0, "closing": 7500.0, "movement": 2500.0},
		                        "feb2024": {"opening": 7500.0, "closing": 8200.0, "movement": 700.0}
		                },
		                "Sales - COMP": {
		                        "jan2024": {"opening": 0.0, "closing": -15000.0, "movement": -15000.0},
		                        "feb2024": {"opening": -15000.0, "closing": -23000.0, "movement": -8000.0}
		                }
		        }
		"""
		# Step 1: Get opening balances from Account Closing Balance if available
		balances_data = self._get_opening_balances(accounts)

		# Step 2: Get GL Entry data (from adjusted date or original period start)
		gl_data = self._get_gl_movements(accounts)

		# Step 3: Calculate running balances
		balances_data = self._calculate_running_balances(balances_data, gl_data)

		return balances_data

	def _get_opening_balances(self, accounts: list[str]) -> dict[str, dict[str, dict[str, float]]]:
		"""
		Get opening balances for accounts, prioritizing `Period Closing Voucher` approach when enabled.
		Steps: check settings → find latest closing voucher → get balances → rebase to period start

		Returns:
		        dict: {account: {period_key: {"opening": balance}}}

		Example:
		        {
		                "Cash - COMP": {"jan2024": {"opening": 1500.0}},
		                "Sales - COMP": {"jan2024": {"opening": 0.0}}
		        }
		"""
		if frappe.get_single_value("Accounts Settings", "ignore_account_closing_balance"):
			return self._get_opening_balances_from_gl(accounts)

		first_period_start = getdate(self.periods[0]["from_date"])
		last_closing_voucher = frappe.db.get_all(
			"Period Closing Voucher",
			filters={
				"docstatus": 1,
				"company": self.company,
				"period_end_date": ("<", first_period_start),
			},
			fields=["period_end_date", "name"],
			order_by="period_end_date desc",
			limit=1,
		)

		if last_closing_voucher:
			closing_balances = self._get_closing_balances(accounts, last_closing_voucher[0].name)

			if closing_balances:
				return self._rebase_closing_balances(
					closing_balances, last_closing_voucher[0].period_end_date
				)

		return self._get_opening_balances_from_gl(accounts)

	def _get_closing_balances(self, account_names: list[str], closing_voucher: str) -> dict:
		acb_table = frappe.qb.DocType("Account Closing Balance")

		query = (
			frappe.qb.from_(acb_table)
			.select(
				acb_table.account,
				(acb_table.debit - acb_table.credit).as_("balance"),
			)
			.where(acb_table.company == self.company)
			.where(acb_table.account.isin(account_names))
			.where(acb_table.period_closing_voucher == closing_voucher)
		)

		query = self._apply_filters(query, acb_table)
		results = self._execute_with_permissions(query, "Account Closing Balance")

		return {row["account"]: row["balance"] for row in results}

	def _rebase_closing_balances(self, closing_data: dict, closing_date: str) -> dict:
		"""Rebase closing balances to align with the report start date."""
		balances_data = {}

		if not closing_data:
			return balances_data

		default_balances = {"opening": 0.0, "closing": 0.0, "movement": 0.0}

		first_period_key = self.periods[0]["key"]
		report_start = getdate(self.periods[0]["from_date"])
		closing_end = getdate(closing_date)

		has_gap = date_diff(report_start, closing_end) > 1

		gap_movements = {}
		if has_gap:
			gap_movements = self._get_gap_movements(list(closing_data.keys()), closing_date, report_start)

		for account, closing_balance in closing_data.items():
			if account not in balances_data:
				balances_data[account] = {}
			if first_period_key not in balances_data[account]:
				balances_data[account][first_period_key] = default_balances.copy()

			gap_adjustment = gap_movements.get(account, 0.0) if has_gap else 0.0
			opening_balance = closing_balance + gap_adjustment

			balances_data[account][first_period_key]["opening"] = opening_balance

		return balances_data

	def _get_gap_movements(self, account_names: list[str], from_date: str, to_date: str) -> dict:
		query, gl_table = self._build_gl_base_query(account_names)

		query = (
			query.select(Sum(gl_table.debit - gl_table.credit).as_("movement"))
			.where(gl_table.posting_date > from_date)
			.where(gl_table.posting_date < to_date)
		)

		results = self._execute_with_permissions(query, "GL Entry")
		return {row["account"]: row["movement"] or 0.0 for row in results}

	def _get_opening_balances_from_gl(self, account_names: list[str]) -> dict:
		"""Calculate opening balances from GL movements when closing vouchers are disabled."""

		# Simulate zero closing balances
		zero_closing_balances = {account: 0.0 for account in account_names}

		# Use a very early date
		earliest_date = "1900-01-01"

		return self._rebase_closing_balances(zero_closing_balances, earliest_date)

	def _get_gl_movements(self, account_names: list[str]) -> list:
		query, gl_table = self._build_gl_base_query(account_names)

		start_date = self.periods[0]["from_date"]
		query = query.where(gl_table.posting_date >= start_date)

		for period in self.periods:
			period_key = period["key"]
			period_start = period["from_date"]
			period_end = period["to_date"]

			movement_column = Sum(
				Case()
				.when(
					(gl_table.posting_date >= period_start) & (gl_table.posting_date <= period_end),
					gl_table.debit - gl_table.credit,
				)
				.else_(0)
			).as_(f"{period_key}_movement")
			query = query.select(movement_column)

		return self._execute_with_permissions(query, "GL Entry")

	def _calculate_running_balances(self, balances_data: dict, gl_data: list) -> dict:
		for row in gl_data:
			account = row["account"]

			if account not in balances_data:
				balances_data[account] = {}

			running_total = 0.0

			first_period_key = self.periods[0]["key"]
			if (
				first_period_key in balances_data.get(account, {})
				and "opening" in balances_data[account][first_period_key]
			):
				running_total = balances_data[account][first_period_key]["opening"]

			for period in self.periods:
				period_key = period["key"]
				movement = row.get(f"{period_key}_movement", 0.0) or 0.0

				if period_key not in balances_data[account]:
					balances_data[account][period_key] = {}

				balances_data[account][period_key]["opening"] = running_total
				balances_data[account][period_key]["movement"] = movement
				balances_data[account][period_key]["closing"] = running_total + movement

				running_total += movement

		return balances_data

	def _build_gl_base_query(self, account_names: list[str]) -> tuple:
		gl_table = frappe.qb.DocType("GL Entry")

		query = (
			frappe.qb.from_(gl_table)
			.select(gl_table.account)
			.where(gl_table.company == self.company)
			.where(gl_table.is_cancelled == 0)
			.where(gl_table.account.isin(account_names))
			.groupby(gl_table.account)
		)

		if not frappe.get_single_value("Accounts Settings", "ignore_is_opening_check_for_reporting"):
			query = query.where(gl_table.is_opening == "No")

		query = self._apply_filters(query, gl_table)
		return query, gl_table

	def _apply_filters(self, query, table):
		"""Apply standard financial filters to query."""
		if self.filters.get("ignore_closing_entries"):
			if hasattr(table, "is_period_closing_voucher_entry"):
				query = query.where(table.is_period_closing_voucher_entry == 0)
			else:
				query = query.where(table.voucher_type != "Period Closing Voucher")

		if self.filters.get("project"):
			if not isinstance(self.filters.get("project"), list):
				self.filters.project = frappe.parse_json(self.filters.get("project"))
			query = query.where(table.project.isin(self.filters.project))

		if self.filters.get("cost_center"):
			self.filters.cost_center = get_cost_centers_with_children(self.filters.cost_center)
			query = query.where(table.cost_center.isin(self.filters.cost_center))

		finance_book = self.filters.get("finance_book")
		if self.filters.get("include_default_book_entries"):
			default_book = frappe.get_cached_value("Company", self.filters.company, "default_finance_book")

			if finance_book and default_book and cstr(finance_book) != cstr(default_book):
				frappe.throw(
					_("To use a different finance book, please uncheck 'Include Default FB Entries'")
				)

			query = query.where(
				(table.finance_book.isin([cstr(finance_book), cstr(default_book), ""]))
				| (table.finance_book.isnull())
			)
		else:
			query = query.where(
				(table.finance_book.isin([cstr(finance_book), ""])) | (table.finance_book.isnull())
			)

		dimensions = get_accounting_dimensions(as_list=False)
		for dimension in dimensions:
			if self.filters.get(dimension.fieldname):
				if frappe.get_cached_value("DocType", dimension.document_type, "is_tree"):
					self.filters[dimension.fieldname] = get_dimension_with_children(
						dimension.document_type, self.filters.get(dimension.fieldname)
					)

				query = query.where(table[dimension.fieldname].isin(self.filters.get(dimension.fieldname)))

		return query

	def _execute_with_permissions(self, query, doctype):
		query_sql = query.walk()

		from frappe.desk.reportview import build_match_conditions

		user_conditions = build_match_conditions(doctype)

		if user_conditions:
			final_query = f"({query_sql}) AND ({user_conditions})"
			return frappe.db.sql(final_query, as_dict=True)
		else:
			return query.run(as_dict=True)

	def get_account_values(self, request: dict, account_data: dict) -> dict[str, list[float]]:
		"""Extract values for each account by period."""
		balance_type = request["balance_type"]
		account_values = frappe._dict()
		num_periods = len(self.periods)

		for account in request["accounts"]:
			values = [0.0] * num_periods

			if account in account_data:
				for i, period in enumerate(self.periods):
					balance_info = account_data[account].get(period["key"], {})
					values[i] = self._get_balance_value(balance_info, balance_type)

			account_values[account] = values

		return account_values

	def _get_balance_value(self, balance_info: dict, balance_type: str) -> float:
		if balance_type == "Opening Balance":
			return balance_info.get("opening", 0.0)
		elif balance_type == "Closing Balance":
			return balance_info.get("closing", 0.0)
		elif balance_type == "Period Movement (Debits - Credits)":
			return balance_info.get("movement", 0.0)
		return 0.0

	def calculate_totals(self, account_values: dict) -> list[float]:
		"""Calculate the total values across all accounts for each period."""
		num_periods = len(self.periods)
		totals = [0.0] * num_periods

		for account_values_list in account_values.values():
			for i in range(num_periods):
				totals[i] += account_values_list[i]

		return totals


class FilterExpressionParser:
	"""Converts filter formulas into database query conditions."""

	def parse(self, formula: str) -> dict:
		"""
		Parse filter formula into structured criteria.
		Supports: ["field", "op", "value"] and {"and/or": [conditions]}

		1. Simple condition: ["field", "operator", "value"]
		   Example: ["account_type", "=", "Income"]

		2. Dictionary-based complex conditions (RECOMMENDED):
		   {
		     "and": [condition1, condition2, ...]  # All conditions must be true
		     "or": [condition1, condition2, ...]   # Any condition can be true
		   }
		   Example: {
		     "and": [
		       ["account_type", "=", "Income"],
		       {"or": [
		         ["category", "=", "Direct Income"],
		         ["category", "=", "Indirect Income"]
		       ]}
		     ]
		   }
		"""
		parsed_formula = ast.literal_eval(formula)

		if isinstance(parsed_formula, dict):
			return self._parse_logical_condition(parsed_formula)

		elif self._is_simple_condition(parsed_formula):
			return {
				"type": "simple",
				"field": parsed_formula[0],
				"operator": parsed_formula[1],
				"value": parsed_formula[2],
			}

		return {}

	def _parse_logical_condition(self, condition_dict: dict) -> dict:
		if not isinstance(condition_dict, dict) or len(condition_dict) != 1:
			return {"type": "invalid"}

		logical_op = next(iter(condition_dict.keys())).lower()
		sub_conditions = condition_dict[logical_op]

		if logical_op not in ["and", "or"] or not isinstance(sub_conditions, list) or len(sub_conditions) < 2:
			return {"type": "invalid"}

		parsed_sub_conditions = []
		for condition in sub_conditions:
			if isinstance(condition, dict):
				parsed_condition = self._parse_logical_condition(condition)
			elif self._is_simple_condition(condition):
				parsed_condition = {
					"type": "simple",
					"field": condition[0],
					"operator": condition[1],
					"value": condition[2],
				}
			else:
				parsed_condition = {"type": "invalid"}

			parsed_sub_conditions.append(parsed_condition)

		return {"type": "logical", "operator": logical_op, "conditions": parsed_sub_conditions}

	def _is_simple_condition(self, parsed) -> bool:
		return (
			isinstance(parsed, list)
			and len(parsed) == 3
			and isinstance(parsed[0], str)
			and isinstance(parsed[1], str)
		)

	def build_condition(self, criteria: dict, table):
		"""Convert criteria into database query conditions."""
		if not criteria or criteria.get("type") == "invalid":
			return None

		if criteria["type"] == "simple":
			return self._create_field_condition(criteria, table)

		elif criteria["type"] == "logical":
			conditions = []
			for sub_criteria in criteria["conditions"]:
				condition = self.build_condition(sub_criteria, table)
				if condition is not None:
					conditions.append(condition)

			if not conditions:
				return None

			if criteria["operator"] == "and":
				return reduce(lambda a, b: a & b, conditions)
			elif criteria["operator"] == "or":
				return reduce(lambda a, b: a | b, conditions)

		return None

	def _create_field_condition(self, criteria: dict, table):
		field_name = criteria["field"]
		operator = criteria["operator"]
		value = criteria["value"]

		if not hasattr(table, field_name):
			return None

		field = getattr(table, field_name)

		if operator in ["=", "=="]:
			return field == value
		elif operator in ["!=", "<>"]:
			return field != value
		elif operator == "in" and isinstance(value, list):
			return field.isin(value)
		elif operator == "not in" and isinstance(value, list):
			return field.notin(value)
		elif operator == "like":
			return field.like(f"%{value}%")
		elif operator == "not like":
			return field.not_like(f"%{value}%")
		elif operator == "is":
			if value is None or (isinstance(value, str) and value.lower() == "set"):
				return field.isnull()
			elif value is None or (isinstance(value, str) and value.lower() == "not set"):
				return field.isnotnull()
			else:
				return field == value

		return None
