# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import ast
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from functools import reduce
from typing import Any, ClassVar, Union

import frappe
from frappe import _
from frappe.query_builder import Case
from frappe.query_builder.functions import Sum
from frappe.utils import cstr, date_diff, flt, getdate

from erpnext import get_company_currency
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
	get_dimension_with_children,
)
from erpnext.accounts.doctype.financial_report_template.financial_report_template import (
	FinancialReportTemplate,
)
from erpnext.accounts.doctype.financial_report_template.financial_report_validation import DependencyValidator
from erpnext.accounts.report.financial_statements import (
	get_columns,
	get_cost_centers_with_children,
	get_period_list,
)
from erpnext.accounts.utils import get_currency_precision

# ============================================================================
# DATA MODELS
# ============================================================================


@dataclass
class PeriodValue:
	"""Represents financial data for a single period"""

	period_key: str
	opening: float = 0.0
	closing: float = 0.0
	movement: float = 0.0

	def get_value(self, balance_type: str) -> float:
		if balance_type == "Opening Balance":
			return self.opening
		elif balance_type == "Closing Balance":
			return self.closing
		elif balance_type == "Period Movement (Debits - Credits)":
			return self.movement
		return 0.0


@dataclass
class AccountData:
	"""Account data across all periods"""

	account_name: str
	period_values: list[PeriodValue] = field(default_factory=list)
	_period_lookup: dict[str, PeriodValue] = field(default_factory=dict)

	def add_period(self, period_value: PeriodValue) -> None:
		"""Add period data in order"""
		if period_value.period_key not in self._period_lookup:
			self.period_values.append(period_value)
		else:
			# Update existing period
			for i, pv in enumerate(self.period_values):
				if pv.period_key == period_value.period_key:
					self.period_values[i] = period_value
					break

		self._period_lookup[period_value.period_key] = period_value

	def get_period(self, period_key: str) -> PeriodValue | None:
		return self._period_lookup.get(period_key)

	def get_values_by_type(self, balance_type: str) -> list[float]:
		return [pv.get_value(balance_type) for pv in self.period_values]

	def has_periods(self) -> bool:
		return len(self.period_values) > 0


@dataclass
class RowData:
	"""Represents a processed template row with calculated values"""

	row: Any  # FinancialReportRow
	values: list[float] = field(default_factory=list)
	account_details: dict[str, AccountData] | None = None
	is_detail_row: bool = False
	parent_reference: str | None = None


@dataclass
class SegmentData:
	"""Represents a segment with its rows and metadata"""

	rows: list[RowData]
	label: str = ""
	index: int = 0
	id: str | None = None

	def __post_init__(self):
		if not self.id and self.index is not None:
			self.id = f"seg_{self.index}"


@dataclass
class ReportContext:
	"""Context object that flows through the pipeline"""

	template: FinancialReportTemplate
	filters: dict[str, Any]
	period_list: list[dict] = field(default_factory=list)
	processed_rows: list[RowData] = field(default_factory=list)
	column_segments: list[list[RowData]] = field(default_factory=list)
	account_data: dict[str, AccountData] = field(default_factory=dict)
	raw_data: dict[str, Any] = field(default_factory=dict)
	show_detailed: bool = False
	currency: str | None = None

	def get_result(self) -> tuple[list[dict], list[dict]]:
		"""Get final formatted columns and data"""
		return self.raw_data.get("columns", []), self.raw_data.get("formatted_data", [])


@dataclass
class FormattingRule:
	"""Rule for applying formatting to rows"""

	condition: callable
	format_properties: dict[str, Any]

	def applies_to(self, row_data: RowData) -> bool:
		return self.condition(row_data)


# ============================================================================
# REPORT ENGINE
# ============================================================================


class FinancialReportEngine:
	def execute(self, filters: dict[str, Any]) -> tuple[list[dict], list[dict]]:
		"""Execute the complete report generation"""
		try:
			# Initialize context
			context = self._initialize_context(filters)

			# Execute
			self.collect_financial_data(context)
			self.process_calculations(context)
			self.format_report_data(context)

			return context.get_result()

		except Exception as e:
			frappe.log_error(f"Financial Report Engine Error: {e!s}")
			frappe.throw(_("Error generating financial report: {0}").format(str(e)))

	def _initialize_context(self, filters: dict[str, Any]) -> ReportContext:
		template_name = filters.get("template_name")
		template = frappe.get_doc("Financial Report Template", template_name)

		if not template:
			frappe.throw(_("Financial Report Template {0} not found").format(template_name))

		if template.disabled:
			frappe.throw(_("Financial Report Template {0} is disabled").format(template_name))

		# Generate periods
		period_list = get_period_list(
			filters.from_fiscal_year,
			filters.to_fiscal_year,
			filters.period_start_date,
			filters.period_end_date,
			filters.filter_based_on,
			filters.periodicity,
			company=filters.company,
		)

		context = ReportContext(
			template=template,
			filters=filters,
			period_list=period_list,
			show_detailed=filters.get("simple_vs_detailed") == "Detailed",
			# TODO: Enhance this to support report currencies
			# after fixing which exchange rate to use for P&L
			currency=get_company_currency(filters.company),
		)
		# Add period_keys to context
		context.raw_data["period_keys"] = [p["key"] for p in period_list]
		return context

	def collect_financial_data(self, context: ReportContext) -> ReportContext:
		collector = DataCollector(context.filters, context.period_list)

		for row in context.template.rows:
			if row.data_source == "Account Data":
				collector.add_account_request(row)

		all_data = collector.collect_all_data()
		context.account_data = all_data["account_data"]
		context.raw_data.update(all_data)

		return context

	def process_calculations(self, context: ReportContext) -> ReportContext:
		processor = RowProcessor(context)
		context.processed_rows = processor.process_all_rows()

		return context

	def format_report_data(self, context: ReportContext) -> ReportContext:
		formatter = DataFormatter(context)
		formatted_data, columns = formatter.format_for_display()

		context.raw_data["formatted_data"] = formatted_data
		context.raw_data["columns"] = columns

		return context


# ============================================================================
# DATA COLLECTION
# ============================================================================


class DataCollector:
	"""Data collector that fetches all data in optimized queries"""

	def __init__(self, filters: dict[str, Any], periods: list[dict]):
		self.filters = filters
		self.periods = periods
		self.company = filters.get("company")
		self.account_requests = []
		self.query_builder = FinancialQueryBuilder(filters, periods)

	def add_account_request(self, row):
		accounts = self._parse_account_filter(row.calculation_formula) if row.calculation_formula else []

		self.account_requests.append(
			{
				"row": row,
				"accounts": accounts,
				"balance_type": row.balance_type,
				"reference_code": row.reference_code,
			}
		)

	def collect_all_data(self) -> dict[str, Any]:
		if not self.account_requests:
			return {"account_data": {}, "summary": {}, "account_details": {}}

		# Get all unique accounts
		all_accounts = set()
		for request in self.account_requests:
			all_accounts.update(request["accounts"])

		all_accounts = list(all_accounts)
		if not all_accounts:
			return {"account_data": {}, "summary": {}, "account_details": {}}

		# Fetch balance data for all accounts
		account_data = self.query_builder.fetch_account_balances(all_accounts)

		# Calculate summaries for each request
		summary = {}
		account_details = {}

		for request in self.account_requests:
			ref_code = request["reference_code"]
			balance_type = request["balance_type"]
			accounts = request["accounts"]

			if not ref_code:
				continue

			total_values = [0.0] * len(self.periods)
			request_account_details = {}

			for account_name in accounts:
				if account_name in account_data:
					account_obj: AccountData = account_data[account_name]
					account_values = account_obj.get_values_by_type(balance_type)

					# Add to totals
					for i, value in enumerate(account_values):
						total_values[i] += value

					# Store for detailed view
					request_account_details[account_name] = account_obj

			summary[ref_code] = total_values
			account_details[ref_code] = request_account_details

		return {"account_data": account_data, "summary": summary, "account_details": account_details}

	def _parse_account_filter(self, filter_formula: str) -> list[str]:
		"""
		Find accounts matching filter criteria.

		Example:
		        Input: '["account_type", "=", "Cash"]'
		        Output: ["Cash - COMP", "Petty Cash - COMP", "Bank - COMP"]
		"""
		filter_parser = FilterExpressionParser()
		criteria = filter_parser.parse(filter_formula)

		account = frappe.qb.DocType("Account")
		query = (
			frappe.qb.from_(account)
			.select(account.name)
			.where(account.disabled == 0)
			.where(account.is_group == 0)
		)

		if self.company:
			query = query.where(account.company == self.company)

		where_condition = filter_parser.build_condition(criteria, account)
		if where_condition is not None:
			query = query.where(where_condition)

		query = query.orderby(account.name)
		result = query.run(as_dict=True)
		return [row.name for row in result]


class FinancialQueryBuilder:
	"""Centralized query builder for financial data"""

	def __init__(self, filters: dict[str, Any], periods: list[dict]):
		self.filters = filters
		self.periods = periods
		self.company = filters.get("company")

	def fetch_account_balances(self, accounts: list[str]) -> dict[str, AccountData]:
		"""
		Fetch account balances for all periods with optimization.
		Steps: get opening balances → fetch GL entries → calculate running totals

		Returns:
		        dict: {account: AccountData}
		"""
		balances_data = self._get_opening_balances(accounts)

		gl_data = self._get_gl_movements(accounts)

		return self._calculate_running_balances(balances_data, gl_data)

	def _get_opening_balances(self, accounts: list[str]) -> dict[str, dict[str, dict[str, float]]]:
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
			closing_voucher = last_closing_voucher[0]
			closing_data = self._get_closing_balances(accounts, closing_voucher.name)

			if closing_data:
				return self._rebase_closing_balances(closing_data, closing_voucher.period_end_date)

		return self._get_opening_balances_from_gl(accounts)

	def _get_closing_balances(self, account_names: list[str], closing_voucher: str) -> dict[str, float]:
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

		query = self._apply_standard_filters(query, acb_table)
		results = self._execute_with_permissions(query, "Account Closing Balance")

		return {row["account"]: row["balance"] for row in results}

	def _rebase_closing_balances(
		self, closing_data: dict[str, float], closing_date: str
	) -> dict[str, dict[str, dict[str, float]]]:
		balances_data = {}

		first_period_key = self.periods[0]["key"]
		report_start = getdate(self.periods[0]["from_date"])
		closing_end = getdate(closing_date)

		has_gap = date_diff(report_start, closing_end) > 1

		gap_movements = {}
		if has_gap:
			gap_movements = self._get_gap_movements(list(closing_data.keys()), closing_date, report_start)

		for account, closing_balance in closing_data.items():
			gap_movement = gap_movements.get(account, 0.0)
			opening_balance = closing_balance + gap_movement

			account_data = AccountData(account)
			account_data.add_period(PeriodValue(first_period_key, opening_balance, 0, 0))
			balances_data[account] = account_data

		return balances_data

	def _get_opening_balances_from_gl(self, accounts: list[str]) -> dict:
		# Simulate zero closing balances
		zero_closing_balances = {account: 0.0 for account in accounts}

		# Use a very early date
		earliest_date = "1900-01-01"

		return self._rebase_closing_balances(zero_closing_balances, earliest_date)

	def _get_gap_movements(self, account_names: list[str], from_date: str, to_date: str) -> dict[str, float]:
		gl_table = frappe.qb.DocType("GL Entry")

		query = (
			frappe.qb.from_(gl_table)
			.select(gl_table.account, Sum(gl_table.debit - gl_table.credit).as_("movement"))
			.where(gl_table.company == self.company)
			.where(gl_table.is_cancelled == 0)
			.where(gl_table.account.isin(account_names))
			.where(gl_table.posting_date > from_date)
			.where(gl_table.posting_date < to_date)
			.groupby(gl_table.account)
		)

		query = self._apply_standard_filters(query, gl_table)
		results = self._execute_with_permissions(query, "GL Entry")

		return {row["account"]: row["movement"] or 0.0 for row in results}

	def _get_gl_movements(self, account_names: list[str]) -> list[dict]:
		gl_table = frappe.qb.DocType("GL Entry")

		query = (
			frappe.qb.from_(gl_table)
			.select(gl_table.account)
			.where(gl_table.company == self.company)
			.where(gl_table.is_cancelled == 0)
			.where(gl_table.account.isin(account_names))
			.where(gl_table.posting_date >= self.periods[0]["from_date"])
			.groupby(gl_table.account)
		)

		if not frappe.get_single_value("Accounts Settings", "ignore_is_opening_check_for_reporting"):
			query = query.where(gl_table.is_opening == "No")

		# Add period-specific columns
		for period in self.periods:
			period_condition = (
				Case()
				.when(
					(gl_table.posting_date >= period["from_date"])
					& (gl_table.posting_date <= period["to_date"]),
					gl_table.debit - gl_table.credit,
				)
				.else_(0)
			)
			query = query.select(Sum(period_condition).as_(period["key"]))

		query = self._apply_standard_filters(query, gl_table)
		return self._execute_with_permissions(query, "GL Entry")

	def _calculate_running_balances(self, balances_data: dict, gl_data: list[dict]) -> dict:
		for row in gl_data:
			account = row["account"]
			if account not in balances_data:
				balances_data[account] = AccountData(account)

			account_data: AccountData = balances_data[account]

			if account_data.has_periods():
				first_period = account_data.get_period(self.periods[0]["key"])
				current_balance = first_period.get_value("Opening Balance") if first_period else 0.0
			else:
				current_balance = 0.0

			for period in self.periods:
				period_key = period["key"]
				movement = row.get(period_key, 0.0)
				closing_balance = current_balance + movement

				account_data.add_period(PeriodValue(period_key, current_balance, closing_balance, movement))

				current_balance = closing_balance

		return balances_data

	def _apply_standard_filters(self, query, table):
		if self.filters.get("ignore_closing_entries"):
			if hasattr(table, "is_period_closing_voucher_entry"):
				query = query.where(table.is_period_closing_voucher_entry == 0)
			else:
				query = query.where(table.voucher_type != "Period Closing Voucher")

		if self.filters.get("project"):
			projects = self.filters.get("project")
			if isinstance(projects, str):
				projects = [projects]
			query = query.where(table.project.isin(projects))

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
		from frappe.desk.reportview import build_match_conditions

		user_conditions = build_match_conditions(doctype)

		if user_conditions:
			return frappe.db.sql(f"{query.walk()} AND {user_conditions}", as_dict=True)
		else:
			return query.run(as_dict=True)


class FilterExpressionParser:
	"""Enhanced filter expression parser"""

	def parse(self, formula: str) -> dict[str, Any]:
		"""
		Parse filter formula into structured criteria.
		Supports: ["field", "op", "value"] and {"and/or": [conditions]}

		1. Simple condition: ["field", "operator", "value"]
		   Example: ["account_type", "=", "Income"]

		2. Dictionary-based complex conditions:
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
		# TODO:
		try:
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

		except Exception:
			frappe.log_error(f"Failed to parse filter formula: {formula}")

		return {"type": "invalid"}

	def _parse_logical_condition(self, condition_dict: dict) -> dict[str, Any]:
		if not isinstance(condition_dict, dict) or len(condition_dict) != 1:
			return {"type": "invalid"}

		logical_op = next(iter(condition_dict.keys())).lower()
		sub_conditions = condition_dict[logical_op]

		if logical_op not in ["and", "or"] or not isinstance(sub_conditions, list):
			return {"type": "invalid"}

		parsed_conditions = []
		for condition in sub_conditions:
			if isinstance(condition, dict):
				parsed_conditions.append(self._parse_logical_condition(condition))
			elif self._is_simple_condition(condition):
				parsed_conditions.append(
					{"type": "simple", "field": condition[0], "operator": condition[1], "value": condition[2]}
				)

		return {"type": "logical", "operator": logical_op, "conditions": parsed_conditions}

	def _is_simple_condition(self, parsed) -> bool:
		return (
			isinstance(parsed, list)
			and len(parsed) == 3
			and isinstance(parsed[0], str)
			and isinstance(parsed[1], str)
		)

	def build_condition(self, criteria: dict, table):
		if criteria.get("type") == "simple":
			return self._build_simple_condition(criteria, table)
		elif criteria.get("type") == "logical":
			return self._build_logical_condition(criteria, table)
		return None

	def _build_simple_condition(self, criteria: dict, table):
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
		elif operator == ">":
			return field > value
		elif operator == ">=":
			return field >= value
		elif operator == "<":
			return field < value
		elif operator == "<=":
			return field <= value

		return None

	def _build_logical_condition(self, criteria: dict, table):
		operator = criteria["operator"]
		conditions = []

		for sub_criteria in criteria["conditions"]:
			condition = self.build_condition(sub_criteria, table)
			if condition is not None:
				conditions.append(condition)

		if not conditions:
			return None

		if operator == "and":
			return reduce(lambda a, b: a & b, conditions)
		elif operator == "or":
			return reduce(lambda a, b: a | b, conditions)

		return None


# ============================================================================
# PROCESS CALCULATIONS
# ============================================================================


class RowProcessor:
	"""
	Processes individual rows of the financial report template.
	Handles dependency resolution and calculation order.
	"""

	def __init__(self, context: ReportContext):
		self.context = context
		self.period_list = context.period_list
		self.row_values = {}  # For formula calculations
		self.dependency_resolver = DependencyResolver(context.template)

	def process_all_rows(self) -> list[RowData]:
		processing_order = self.dependency_resolver.get_processing_order()
		processed_rows = []

		# Get account data from context
		account_summary = self.context.raw_data.get("summary", {})
		account_details = self.context.raw_data.get("account_details", {})

		for row in processing_order:
			row_data = self._process_single_row(row, account_summary, account_details)
			processed_rows.append(row_data)

		processed_rows.sort(key=lambda x: getattr(x.row, "idx", 0) or 0)

		return processed_rows

	def _process_single_row(self, row, account_summary: dict, account_details: dict) -> RowData:
		if row.data_source == "Account Data":
			return self._process_account_row(row, account_summary, account_details)
		elif row.data_source == "Custom API":
			return self._process_api_row(row)
		elif row.data_source == "Calculated Amount":
			return self._process_formula_row(row)
		elif row.data_source == "Blank Line":
			return self._process_blank_row(row)
		elif row.data_source == "Column Break":
			return self._process_column_break_row(row)
		else:
			return RowData(row=row, values=[0.0] * len(self.period_list))

	def _process_account_row(self, row, account_summary: dict, account_details: dict) -> RowData:
		ref_code = row.reference_code
		values = account_summary.get(ref_code, [0.0] * len(self.period_list))
		details = account_details.get(ref_code, {})

		if ref_code:
			self.row_values[ref_code] = values

		return RowData(row=row, values=values, account_details=details)

	def _process_api_row(self, row) -> RowData:
		api_path = row.calculation_formula
		# TODO

		try:
			module_path, method_name = api_path.rsplit(".", 1)
			module = frappe.get_module(module_path)
			method = getattr(module, method_name)

			context = {
				"filters": self.context.filters,
				"periods": self.period_list,
				"row": row,
				"company": self.context.filters.get("company"),
			}

			values = method(context)
		except Exception as e:
			frappe.log_error(f"Custom API Error: {api_path} - {e!s}")
			values = [0.0] * len(self.period_list)

		if row.reference_code:
			self.row_values[row.reference_code] = values

		return RowData(row=row, values=values)

	def _process_formula_row(self, row) -> RowData:
		calculator = FormulaCalculator(self.row_values, self.period_list)
		values = calculator.evaluate_formula(row.calculation_formula)

		if row.reference_code:
			self.row_values[row.reference_code] = values

		return RowData(row=row, values=values)

	def _process_blank_row(self, row) -> RowData:
		return RowData(row=row, values=[""] * len(self.period_list))

	def _process_column_break_row(self, row) -> RowData:
		return RowData(row=row, values=[])


class DependencyResolver:
	"""Optimized dependency resolver with better circular reference detection"""

	def __init__(self, template):
		self.template: FinancialReportTemplate = template
		self.rows = template.rows
		self.row_map = {row.reference_code: row for row in self.rows if row.reference_code}
		self.dependencies = {}
		self._validate_dependencies()

	def _validate_dependencies(self):
		"""Validate dependencies using the new validation framework"""

		validator = DependencyValidator(self.template)
		result = validator.validate()

		if result.issues:
			error_messages = [str(issue) for issue in result.issues]
			frappe.throw("<br><br>".join(error_messages))

		self.dependencies = validator.dependencies

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
			ordered_formula_rows = self._topological_sort(formula_rows)
			ordered_rows.extend(ordered_formula_rows)

		ordered_rows.extend(other_rows)

		return ordered_rows

	def _topological_sort(self, formula_rows: list) -> list:
		formula_row_map = {row.reference_code: row for row in formula_rows if row.reference_code}

		# Calculate in-degree
		in_degree = {code: 0 for code in formula_row_map.keys()}
		for code, deps in self.dependencies.items():
			if code in in_degree:
				for dep in deps:
					if dep in in_degree:
						in_degree[code] += 1

		# Topological sort
		queue = [code for code, degree in in_degree.items() if degree == 0]
		result = []

		while queue:
			current = queue.pop(0)
			result.append(formula_row_map[current])

			for code, deps in self.dependencies.items():
				if current in deps and code in in_degree:
					in_degree[code] -= 1
					if in_degree[code] == 0:
						queue.append(code)

		# Add any remaining formula rows
		for row in formula_rows:
			if row not in result:
				result.append(row)

		return result


class FormulaCalculator:
	"""Enhanced formula calculator with better error handling"""

	def __init__(self, row_data: dict[str, list[float]], period_list: list[dict]):
		self.row_data = row_data
		self.period_list = period_list
		self.precision = get_currency_precision()

	def evaluate_formula(self, formula: str) -> list[float]:
		formula = self._preprocess_formula(formula)
		results = []

		for i in range(len(self.period_list)):
			result = self._evaluate_for_period(formula, i)
			results.append(result)

		return results

	def _evaluate_for_period(self, formula: str, period_index: int) -> float:
		# TODO: consistent error handling
		try:
			context = self._build_context(period_index)
			result = frappe.safe_eval(formula, context)
			return flt(result, self.precision)

		except ZeroDivisionError:
			frappe.log_error(f"Division by zero in formula: {formula}")
			return 0.0
		except Exception as e:
			frappe.log_error(f"Formula evaluation error: {formula} - {e!s}")
			return 0.0

	def _preprocess_formula(self, formula: str) -> str:
		if not formula or not isinstance(formula, str):
			return ""

		return formula.strip()

	def _build_context(self, period_index: int) -> dict[str, Any]:
		context = {}

		# row values
		for code, values in self.row_data.items():
			if period_index < len(values):
				context[code] = values[period_index] or 0.0
			else:
				context[code] = 0.0

		# math functions
		context.update(FormulaCalculator._get_math_functions())

		return context

	@staticmethod
	def _get_math_functions() -> dict[str, Any]:
		return {
			"abs": abs,
			"round": round,
			"min": min,
			"max": max,
			"sum": sum,
			"sqrt": math.sqrt,
			"pow": math.pow,
			"ceil": math.ceil,
			"floor": math.floor,
		}


# ============================================================================
# DATA FORMATTING
# ============================================================================


class DataFormatter:
	def __init__(self, context: ReportContext):
		self.context = context
		self.formatting_engine = FormattingEngine()

		self.organizer = SegmentOrganizer(context.processed_rows)

		if self.organizer.is_single_segment:
			self.formatter = SingleSegmentFormatter(context, self.formatting_engine)
		else:
			self.formatter = MultiSegmentFormatter(context, self.formatting_engine)

		if context.show_detailed:
			self._expand_segments_with_details()

	def format_for_display(self) -> tuple[list[dict], list[dict]]:
		formatted_data = self._format_rows()
		columns = self._generate_columns()
		return formatted_data, columns

	def _format_rows(self) -> list[dict]:
		formatted_data = []

		for row_index in range(self.organizer.max_rows):
			formatted_row = self.formatter.format_row(self.organizer.segments, row_index)

			if formatted_row:  # Always include rows that were formatted
				# Add metadata
				formatted_row["_segment_info"] = {
					"total_segments": len(self.organizer.segments),
					"segment_labels": self.organizer.segment_labels,
					"period_keys": [p["key"] for p in self.context.period_list],  # Add period keys
				}

				formatted_data.append(formatted_row)

		return formatted_data

	def _generate_columns(self) -> list[dict]:
		base_columns = get_columns(
			self.context.filters.get("periodicity"),
			self.context.period_list,
			self.context.filters.get("accumulated_values"),
			self.context.filters.get("company"),
		)

		return self.formatter.get_columns(self.organizer.segments, base_columns)

	def _expand_segments_with_details(self):
		for segment in self.organizer.segments:
			expanded_rows = []

			for row_data in segment.rows:
				expanded_rows.append(row_data)

				if row_data.account_details:
					detail_rows = DetailRowBuilder(self.context.filters, row_data).build()
					expanded_rows.extend(detail_rows)

			segment.rows = expanded_rows


class FormattingEngine:
	"""Manages formatting rules and application"""

	def __init__(self):
		self.initialize_rules()

	def initialize_rules(self):
		self.rules = [
			FormattingRule(
				condition=lambda rd: getattr(rd.row, "bold_text", False), format_properties={"bold": True}
			),
			FormattingRule(
				condition=lambda rd: getattr(rd.row, "italic_text", False), format_properties={"italic": True}
			),
			FormattingRule(
				condition=lambda rd: rd.is_detail_row, format_properties={"is_detail": True, "prefix": "• "}
			),
			FormattingRule(
				condition=lambda rd: getattr(rd.row, "reverse_sign", False),
				format_properties={"reverse_sign": True},
			),
			FormattingRule(
				condition=lambda rd: getattr(rd.row, "warn_if_negative", False),
				format_properties={"warn_if_negative": True},
			),
			FormattingRule(
				condition=lambda rd: getattr(rd.row, "data_source", "") == "Blank Line",
				format_properties={"is_blank_line": True},
			),
		]

	def get_formatting(self, row_data: RowData) -> dict[str, Any]:
		formatting = {}
		for rule in self.rules:
			if rule.applies_to(row_data):
				formatting.update(rule.format_properties)
		return formatting


class SegmentOrganizer:
	"""Handles segment organization by `Column Break` and metadata extraction"""

	def __init__(self, processed_rows: list[RowData]):
		self.segments = self._organize_into_segments(processed_rows)

	def _organize_into_segments(self, rows: list[RowData]) -> list[SegmentData]:
		segments = []
		current_rows = []
		segment_index = 0
		pending_label = ""

		for row_data in rows:
			if not self._should_show_row(row_data):
				continue

			if row_data.row.data_source == "Column Break":
				# Save current segment with pending label from previous column break
				if current_rows:
					segments.append(SegmentData(rows=current_rows, label=pending_label, index=segment_index))
					segment_index += 1
					current_rows = []

				# Label for the next segment
				pending_label = getattr(row_data.row, "display_name", "") or ""
				pending_label = pending_label.strip() if pending_label else ""
			else:
				current_rows.append(row_data)

		# Add final segment
		if current_rows or not segments:
			segments.append(SegmentData(rows=current_rows, label=pending_label, index=segment_index))

		return segments

	@property
	def is_single_segment(self) -> bool:
		return len(self.segments) == 1

	@property
	def max_rows(self) -> int:
		return max(len(seg.rows) for seg in self.segments) if self.segments else 0

	@property
	def segment_labels(self) -> dict[int, str]:
		return {seg.index: seg.label for seg in self.segments if seg.label}

	def _should_show_row(self, row_data: RowData) -> bool:
		row = row_data.row

		# Always show blank lines
		if row.data_source == "Blank Line":
			return True

		if getattr(row, "hidden_calculation", False):
			return False

		if getattr(row, "hide_when_empty", False):
			significant_values = [
				val for val in row_data.values if isinstance(val, int | float) and abs(flt(val)) > 0.01
			]
			return len(significant_values) > 0

		return True


class RowFormatterBase(ABC):
	def __init__(self, context: ReportContext, formatting_engine: FormattingEngine):
		self.context = context
		self.period_list = context.period_list
		self.formatting_engine = formatting_engine

	@abstractmethod
	def format_row(self, segments: list[SegmentData], row_index: int) -> dict[str, Any]:
		pass

	@abstractmethod
	def get_columns(self, segments: list[SegmentData], base_columns: list[dict]) -> list[dict]:
		pass

	def _get_values(self, row_data: RowData) -> dict[str, Any]:
		values = {
			"account": getattr(row_data.row, "display_name", "") or "",
			"indent": getattr(row_data.row, "indentation_level", 0),
			"account_name": getattr(row_data.row, "account", "") or "",
			"currency": getattr(self.context.currency, "currency", "") or "",
			"period_start_date": getattr(self.context.filters, "period_start_date", "") or "",
			"period_end_date": getattr(self.context.filters, "period_end_date", "") or "",
		}

		for i, period in enumerate(self.period_list):
			values[period["key"]] = self._get_period_value(row_data, i)

		return values

	def _get_period_value(self, row_data: RowData, period_index: int) -> Any:
		if period_index < len(row_data.values):
			value = row_data.values[period_index]
			if getattr(row_data.row, "reverse_sign", False):
				value = -value
			return value

		return ""


class SingleSegmentFormatter(RowFormatterBase):
	def format_row(self, segments: list[SegmentData], row_index: int) -> dict[str, Any]:
		if not segments or row_index >= len(segments[0].rows):
			return {}

		row_data = segments[0].rows[row_index]

		formatted = self._get_values(row_data)

		formatting = self.formatting_engine.get_formatting(row_data)
		formatted.update(formatting)

		return formatted

	def get_columns(self, segments: list[SegmentData], base_columns: list[dict]) -> list[dict]:
		return base_columns


class MultiSegmentFormatter(RowFormatterBase):
	def format_row(self, segments: list[SegmentData], row_index: int) -> dict[str, Any]:
		formatted = {}

		for segment in segments:
			if row_index < len(segment.rows):
				row_data = segment.rows[row_index]
				self._add_segment_data(formatted, row_data, segment)
			else:
				self._add_empty_segment(formatted, segment)

		return formatted

	def get_columns(self, segments: list[SegmentData], base_columns: list[dict]) -> list[dict]:
		columns = []

		# TODO: Refactor
		for segment in segments:
			for col in base_columns:
				new_col = col.copy()

				new_col["fieldname"] = f"{segment.id}_{col['fieldname']}"

				if col["fieldname"] == "account":
					new_col["label"] = segment.label or f"Account (Segment {segment.index + 1})"

				if segment.label and col["fieldname"] in [p["key"] for p in self.period_list]:
					new_col["label"] = f"{segment.label} - {col['label']}"

				columns.append(new_col)

		return columns

	def _add_segment_data(self, formatted: dict, row_data: RowData, segment: SegmentData):
		segment_values = self._get_values(row_data)

		for key, value in segment_values.items():
			formatted[f"{segment.id}_{key}"] = value

		if "segment_values" not in formatted:
			formatted["segment_values"] = {}

		formatting = self.formatting_engine.get_formatting(row_data)
		segment_values.update(formatting)
		formatted["segment_values"][f"{segment.id}"] = segment_values

	def _add_empty_segment(self, formatted: dict, segment: SegmentData):
		formatted[f"account_{segment.id}"] = ""
		for period in self.period_list:
			formatted[f"{segment.id}_{period['key']}"] = ""

		formatted["segment_values"][f"{segment.id}"] = {"is_blank_line": True}


class DetailRowBuilder:
	"""Builds detail rows for account breakdown"""

	def __init__(self, filters: dict, parent_row_data: RowData):
		self.filters = filters
		self.parent_row_data = parent_row_data

	def build(self) -> list[RowData]:
		if not self.parent_row_data.account_details:
			return []

		detail_rows = []
		parent_row = self.parent_row_data.row

		for account_name, account_data in self.parent_row_data.account_details.items():
			detail_row = self._create_detail_row_object(account_name, parent_row)

			balance_type = getattr(parent_row, "balance_type", "Closing Balance")
			values = account_data.get_values_by_type(balance_type)

			detail_row_data = RowData(
				row=detail_row,
				values=values,
				is_detail_row=True,
				parent_reference=parent_row.reference_code,
			)

			detail_rows.append(detail_row_data)

		return detail_rows

	def _create_detail_row_object(self, account_name: str, parent_row):
		short_name = account_name.rsplit(" - ", 1)[0].strip()

		return type(
			"DetailRow",
			(),
			{
				"display_name": short_name,
				"account": account_name,
				"account_name": short_name,
				"data_source": "Account Detail",
				"indentation_level": getattr(parent_row, "indentation_level", 0) + 1,
				"bold_text": False,
				"italic_text": True,
				"reverse_sign": getattr(parent_row, "reverse_sign", False),
				"warn_if_negative": getattr(parent_row, "warn_if_negative", False),
				"hide_when_empty": getattr(parent_row, "hide_when_empty", False),
				"hidden_calculation": False,
			},
		)()
