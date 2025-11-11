# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import ast
import json
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import reduce
from typing import Any, Union

import frappe
from frappe import _
from frappe.database.operator_map import OPERATOR_MAP
from frappe.query_builder import Case
from frappe.query_builder.functions import Sum
from frappe.utils import cstr, date_diff, flt, getdate
from pypika.terms import LiteralValue

from erpnext import get_company_currency
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
	get_dimension_with_children,
)
from erpnext.accounts.doctype.financial_report_row.financial_report_row import FinancialReportRow
from erpnext.accounts.doctype.financial_report_template.financial_report_template import (
	FinancialReportTemplate,
)
from erpnext.accounts.doctype.financial_report_template.financial_report_validation import (
	AccountFilterValidator,
	CalculationFormulaValidator,
	DependencyValidator,
)
from erpnext.accounts.report.financial_statements import (
	get_columns,
	get_cost_centers_with_children,
	get_period_list,
)
from erpnext.accounts.utils import get_children, get_currency_precision

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

	def copy(self):
		return PeriodValue(
			period_key=self.period_key, opening=self.opening, closing=self.closing, movement=self.movement
		)


@dataclass
class AccountData:
	"""Account data across all periods"""

	account_name: str
	period_values: dict[str, PeriodValue] = field(default_factory=dict)

	def add_period(self, period_value: PeriodValue) -> None:
		self.period_values[period_value.period_key] = period_value

	def get_period(self, period_key: str) -> PeriodValue | None:
		return self.period_values.get(period_key)

	def get_values_by_type(self, balance_type: str) -> list[float]:
		return [pv.get_value(balance_type) for pv in self.period_values.values()]

	def get_ordered_values(self, period_keys: list[str], balance_type: str) -> list[float]:
		return [
			self.period_values[key].get_value(balance_type) if key in self.period_values else 0.0
			for key in period_keys
		]

	def has_periods(self) -> bool:
		return len(self.period_values) > 0

	def accumulate_values(self) -> None:
		for period_value in self.period_values.values():
			period_value.movement += period_value.opening
			# closing is accumulated by default

	def unaccumulate_values(self) -> None:
		for period_value in self.period_values.values():
			period_value.closing -= period_value.opening
			# movement is unaccumulated by default

	def copy(self):
		copied = AccountData(account_name=self.account_name)
		copied.period_values = {k: v.copy() for k, v in self.period_values.items()}
		return copied

	def reverse_values(self) -> None:
		for period_value in self.period_values.values():
			period_value.opening = -period_value.opening if period_value.opening else 0.0
			period_value.closing = -period_value.closing if period_value.closing else 0.0
			period_value.movement = -period_value.movement if period_value.movement else 0.0


@dataclass
class RowData:
	"""Represents a processed template row with calculated values"""

	row: FinancialReportRow
	values: list[float] = field(default_factory=list)
	account_details: dict[str, AccountData] | None = None
	is_detail_row: bool = False
	parent_reference: str | None = None


@dataclass
class SegmentData:
	"""Represents a segment with its rows and metadata"""

	rows: list[RowData] = field(default_factory=list)
	label: str = ""
	index: int = 0

	@property
	def id(self) -> str:
		return f"seg_{self.index}"


@dataclass
class SectionData:
	"""Represents a horizontal section containing multiple column segments"""

	segments: list[SegmentData]
	label: str = ""
	index: int = 0

	@property
	def id(self) -> str:
		return f"section_{self.index}"


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
		return (
			self.raw_data.get("columns", []),
			self.raw_data.get("formatted_data", []),
			None,
			self.raw_data.get("chart", {}),
		)


@dataclass
class FormattingRule:
	"""Rule for applying formatting to rows"""

	condition: callable
	format_properties: Union[dict[str, Any], callable]  # noqa: UP007

	def applies_to(self, row_data: RowData) -> bool:
		return self.condition(row_data)

	def get_properties(self, row_data: RowData) -> dict[str, Any]:
		"""Get the format properties, handling both static and dynamic cases"""
		if callable(self.format_properties):
			return self.format_properties(row_data)
		return self.format_properties


# ============================================================================
# REPORT ENGINE
# ============================================================================


class FinancialReportEngine:
	def execute(self, filters: dict[str, Any]) -> tuple[list[dict], list[dict]]:
		"""Execute the complete report generation"""
		self._validate_filters(filters)

		# Initialize context
		context = self._initialize_context(filters)

		# Execute
		self.collect_financial_data(context)
		self.process_calculations(context)
		self.format_report_data(context)
		self.apply_view_transformation(context)

		# Chart
		self.generate_chart_data(context)
		return context.get_result()

	def _validate_filters(self, filters: dict[str, Any]) -> None:
		required_filters = ["report_template", "period_start_date", "period_end_date"]

		for filter_key in required_filters:
			if not filters.get(filter_key):
				frappe.throw(_("Missing required filter: {0}").format(filter_key))

		if filters.get("presentation_currency"):
			frappe.msgprint(_("Currency filters are currently unsupported in Custom Financial Report."))

		# Margin view is dependent on first row being an income account. Hence not supported.
		# Way to implement this would be using calculated rows with formulas.
		supported_views = ("Report", "Growth")
		if (view := filters.get("selected_view")) and view not in supported_views:
			frappe.msgprint(_("{0} view is currently unsupported in Custom Financial Report.").format(view))

	def _initialize_context(self, filters: dict[str, Any]) -> ReportContext:
		template_name = filters.get("report_template")
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

		# Support both old and new field names for backward compatibility
		show_detailed = filters.get("show_account_details") == "Account Breakdown"

		context = ReportContext(
			template=template,
			filters=filters,
			period_list=period_list,
			show_detailed=show_detailed,
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

	def apply_view_transformation(self, context: ReportContext) -> ReportContext:
		if context.filters.get("selected_view") == "Growth":
			transformer = GrowthViewTransformer(context)
			transformer.transform()

		# Default is "Report" view - no transformation needed

		return context

	def generate_chart_data(self, context: ReportContext) -> dict[str, Any]:
		generator = ChartDataGenerator(context)
		generator.generate()

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
		self.account_fields = {field.fieldname for field in frappe.get_meta("Account").fields}

	def add_account_request(self, row):
		accounts = self._parse_account_filter(self.company, row)

		self.account_requests.append(
			{
				"row": row,
				"accounts": accounts,
				"balance_type": row.balance_type,
				"reference_code": row.reference_code,
				"reverse_sign": row.reverse_sign,
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
		period_keys = [p["key"] for p in self.periods]

		for request in self.account_requests:
			ref_code = request["reference_code"]
			if not ref_code:
				continue

			balance_type = request["balance_type"]
			accounts = request["accounts"]

			total_values = [0.0] * len(self.periods)
			request_account_details = {}

			for account_name in accounts:
				if account_name not in account_data:
					continue

				account_obj: AccountData = account_data[account_name].copy()
				if request["reverse_sign"]:
					account_obj.reverse_values()

				account_values = account_obj.get_ordered_values(period_keys, balance_type)

				# Add to totals
				for i, value in enumerate(account_values):
					total_values[i] += value

				# Store for detailed view
				request_account_details[account_name] = account_obj

			summary[ref_code] = total_values
			account_details[ref_code] = request_account_details

		return {"account_data": account_data, "summary": summary, "account_details": account_details}

	@staticmethod
	def _parse_account_filter(company, report_row) -> list[str]:
		"""
		Find accounts matching filter criteria.

		Example:
		                Input: '["account_type", "=", "Cash"]'
		                Output: ["Cash - COMP", "Petty Cash - COMP", "Bank - COMP"]
		"""
		filter_parser = FilterExpressionParser()

		account = frappe.qb.DocType("Account")
		query = (
			frappe.qb.from_(account)
			.select(account.name)
			.where(account.disabled == 0)
			.where(account.is_group == 0)
		)

		if company:
			query = query.where(account.company == company)

		where_condition = filter_parser.build_condition(report_row, account)
		if where_condition is None:
			return []

		query = query.where(where_condition)
		query = query.orderby(account.name)
		result = query.run(as_dict=True)
		return [row.name for row in result]

	@staticmethod
	def get_filtered_accounts(company: str, account_rows: list) -> list[str]:
		filter_parser = FilterExpressionParser()

		account = frappe.qb.DocType("Account")
		query = (
			frappe.qb.from_(account)
			.select(account.name)
			.distinct()
			.where(account.disabled == 0)
			.where(account.is_group == 0)
			.orderby(account.name)
		)

		if company:
			query = query.where(account.company == company)

		if conditions := filter_parser.build_conditions(account_rows, account):
			query = query.where(conditions)

		return query.run(pluck=True)


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
		self._calculate_running_balances(balances_data, gl_data)
		self._handle_balance_accumulation(balances_data)

		return balances_data

	def _get_opening_balances(self, accounts: list[str]) -> dict[str, dict[str, dict[str, float]]]:
		"""
		Return opening balances for *all accounts* defaulting to zero.
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
			closing_voucher = last_closing_voucher[0]
			closing_data = self._get_closing_balances(accounts, closing_voucher.name)

			if sum(closing_data.values()) != 0.0:
				return self._rebase_closing_balances(closing_data, closing_voucher.period_end_date)

		return self._get_opening_balances_from_gl(accounts)

	def _get_closing_balances(self, account_names: list[str], closing_voucher: str) -> dict[str, float]:
		closing_balances = {account: 0.0 for account in account_names}
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

		for row in results:
			closing_balances[row["account"]] = row["balance"]

		return closing_balances

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

		# Accounts with no movements
		for account_data in balances_data.values():
			for period in self.periods:
				period_key = period["key"]
				if period_key not in account_data.period_values:
					account_data.add_period(PeriodValue(period_key, 0.0, 0.0, 0.0))

	def _handle_balance_accumulation(self, balances_data):
		for account_data in balances_data.values():
			account_data: AccountData

			accumulated_values = self.filters.get("accumulated_values")

			if accumulated_values is None:
				# respect user setting if not in filters
				# closing = accumulated
				# movement = unaccumulated
				continue

			# for legacy reports
			elif accumulated_values:
				account_data.accumulate_values()
			else:
				account_data.unaccumulate_values()

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
			query = query.where(LiteralValue(user_conditions))

		return query.run(as_dict=True)


class FilterExpressionParser:
	"""Direct filter expression to SQL condition builder"""

	def __init__(self):
		self.validator = AccountFilterValidator()

	def build_conditions(self, report_rows, table):
		conditions = []
		for row in report_rows or []:
			condition = self.build_condition(row, table)
			if condition is not None:
				conditions.append(condition)

		# ensure brackets in or condition
		return reduce(lambda a, b: (a) | (b), conditions)

	def build_condition(self, report_row, table):
		"""
		Build SQL condition directly from filter formula.

		Supports:
		1. Simple condition: ["field", "operator", "value"]
		   Example: ["account_type", "=", "Income"]

		2. Complex logical conditions:
		   {"and": [condition1, condition2, ...]}  # All conditions must be true
		   {"or": [condition1, condition2, ...]}   # Any condition can be true

		   Example:
		   {
		         "and": [
		           ["account_type", "=", "Income"],
		           {"or": [
		                 ["category", "=", "Direct Income"],
		                 ["category", "=", "Indirect Income"]
		           ]}
		         ]
		   }

		Returns:
		        SQL condition object or None if invalid
		"""
		filter_formula = report_row.calculation_formula
		if not filter_formula:
			return None

		errors = self.validator.validate(report_row)
		if not errors.is_valid:
			error_messages = [str(issue) for issue in errors.issues]
			frappe.log_error(f"Filter validation errors found:\n{'<br><br>'.join(error_messages)}")
			return None

		try:
			parsed = ast.literal_eval(filter_formula)
			return self._build_from_parsed(parsed, table)
		except (ValueError, SyntaxError) as e:
			frappe.log_error(f"Invalid filter formula syntax: {filter_formula} - {e}")
			return None
		except Exception as e:
			frappe.log_error(f"Failed to build condition from formula: {filter_formula} - {e}")
			return None

	def _build_from_parsed(self, parsed, table):
		if isinstance(parsed, dict):
			return self._build_logical_condition(parsed, table)

		if isinstance(parsed, list):
			return self._build_simple_condition(parsed, table)

		return None

	def _build_simple_condition(self, condition_list: list[str, str, str | float], table):
		field_name, operator, value = condition_list

		if value is None:
			return None

		field = getattr(table, field_name, None)
		operator_fn = OPERATOR_MAP.get(operator.casefold())

		if "like" in operator.casefold() and "%" not in value:
			value = f"%{value}%"

		return operator_fn(field, value)

	def _build_logical_condition(self, condition_dict: dict, table):
		"""Build SQL condition from logical {"and/or": [...]} format"""

		logical_op = next(iter(condition_dict.keys())).lower()
		sub_conditions = condition_dict.get(logical_op)

		# recursive
		built_conditions = []
		for sub_condition in sub_conditions:
			condition = self._build_from_parsed(sub_condition, table)
			if condition is not None:
				built_conditions.append(condition)

		if not built_conditions:
			return None

		if len(built_conditions) == 1:
			return built_conditions[0]

		# combine
		if logical_op == "and":
			return reduce(lambda a, b: a & b, built_conditions)
		else:  # logical_op == "or"
			return reduce(lambda a, b: a | b, built_conditions)


class FormulaFieldExtractor:
	"""Extract field values from filter formulas without SQL execution"""

	def __init__(self, field_name: str, exclude_operators: list[str] | None = None):
		"""
		Initialize field extractor.

		Args:
		    field_name: The field to extract values for (e.g., "account_category")
		    exclude_operators: List of operators to exclude (e.g., ["like"])
		"""
		self.field_name = field_name
		self.exclude_operators = [op.lower() for op in (exclude_operators or [])]

	def extract_from_rows(self, rows: list) -> set:
		values = set()

		for row in rows:
			if not hasattr(row, "calculation_formula") or not row.calculation_formula:
				continue

			try:
				parsed = ast.literal_eval(row.calculation_formula)
				self._extract_recursive(parsed, values)
			except (ValueError, SyntaxError):
				continue  # Skip rows with invalid formulas

		return values

	def _extract_recursive(self, parsed, values: set):
		if isinstance(parsed, list) and len(parsed) == 3:
			# Simple condition: ["field", "operator", "value"]
			field, operator, value = parsed

			if field == self.field_name and operator.lower() not in self.exclude_operators:
				if isinstance(value, str):
					values.add(value)
				elif isinstance(value, list):
					# Handle "in" operator with list of values
					values.update(v for v in value if isinstance(v, str))

		elif isinstance(parsed, dict):
			# Logical condition: {"and/or": [...]}
			for sub_conditions in parsed.values():
				if isinstance(sub_conditions, list):
					for sub_condition in sub_conditions:
						self._extract_recursive(sub_condition, values)


class FormulaFieldUpdater:
	"""Update field values in filter formulas"""

	def __init__(
		self, field_name: str, value_mapping: dict[str, str], exclude_operators: list[str] | None = None
	):
		"""
		Initialize field updater.

		Args:
		    field_name: The field to update values for (e.g., "account_category")
		    value_mapping: Mapping of old values to new values (e.g., {"Old Name": "New Name"})
		    exclude_operators: List of operators to exclude from updates (e.g., ["like", "not like"])
		"""
		self.field_name = field_name
		self.value_mapping = value_mapping
		self.exclude_operators = [op.lower() for op in (exclude_operators or [])]

	def update_in_rows(self, rows: list) -> dict[str, dict[str, str]]:
		updated_rows = {}

		for row_name, formula in rows.items():
			if not formula:
				continue

			try:
				parsed = ast.literal_eval(formula)
				updated = self._update_recursive(parsed)

				if updated != parsed:
					updated_formula = json.dumps(updated)
					updated_rows[row_name] = {"calculation_formula": updated_formula}

			except (ValueError, SyntaxError):
				continue  # Skip rows with invalid formulas

		if updated_rows:
			frappe.db.bulk_update("Financial Report Row", updated_rows, update_modified=False)

		return updated_rows

	def _update_recursive(self, parsed):
		if isinstance(parsed, list) and len(parsed) == 3:
			# Simple condition: ["field", "operator", "value"]
			field, operator, value = parsed

			if field == self.field_name and operator.lower() not in self.exclude_operators:
				updated_value = self._update_value(value)
				return [field, operator, updated_value]

			return parsed

		elif isinstance(parsed, dict):
			# Logical condition: {"and/or": [...]}
			updated_dict = {}
			for key, sub_conditions in parsed.items():
				updated_conditions = [
					self._update_recursive(sub_condition) for sub_condition in sub_conditions
				]
				updated_dict[key] = updated_conditions

			return updated_dict

		return parsed

	def _update_value(self, value):
		if isinstance(value, str):
			return self.value_mapping.get(value, value)

		elif isinstance(value, list):
			# Handle "in" operator with list of values
			return [self.value_mapping.get(v, v) if isinstance(v, str) else v for v in value]

		return value


@frappe.whitelist()
def get_filtered_accounts(company: str, account_rows: str | list):
	frappe.has_permission("Financial Report Template", ptype="read", throw=True)

	if isinstance(account_rows, str):
		account_rows = json.loads(account_rows, object_hook=frappe._dict)

	return DataCollector.get_filtered_accounts(company, account_rows)


@frappe.whitelist()
def get_children_accounts(
	doctype: str,
	parent: str,
	company: str,
	filtered_accounts: list[str] | str | None = None,
	missed: bool = False,
	is_root: bool = False,
	include_disabled: bool = False,
):
	"""
	Get children accounts based on the provided filters to view in tree.

	Args:
	    parent: The parent account to get children for.
	    company: The company to filter accounts by.
	    account_rows: Template rows with `Data Source` == `Account Data`.
	    missed:
	                - If True, only missed by filters accounts will be included.
	                - If False, only filtered accounts will be included.
	    is_root: Whether the parent is a root account.
	    include_disabled: Whether to include disabled accounts.

	Example:
	```python
	[
	    {
	        value: "Current Liabilities - WP",
	        expandable: 1,
	        root_type: "Liability",
	        account_currency: "USD",
	        parent: "Source of Funds (Liabilities) - WP",
	    },
	    {
	        value: "Non-Current Liabilities - WP",
	        expandable: 1,
	        root_type: "Liability",
	        account_currency: "USD",
	        parent: "Source of Funds (Liabilities) - WP",
	    },
	]
	```
	"""
	frappe.has_permission(doctype, ptype="read", throw=True)

	children_accounts = get_children(
		doctype, parent, company, is_root=is_root, include_disabled=include_disabled
	)

	if not children_accounts:
		return []

	if isinstance(filtered_accounts, str):
		filtered_accounts = frappe.parse_json(filtered_accounts)

	if not filtered_accounts:
		return children_accounts if missed else []

	valid_accounts = []

	for account in children_accounts:
		if account.expandable:
			valid_accounts.append(account)
			continue

		is_in_filtered = account.value in filtered_accounts

		if (missed and not is_in_filtered) or (not missed and is_in_filtered):
			valid_accounts.append(account)

	return valid_accounts


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
		elif row.data_source == "Section Break":
			return self._process_section_break_row(row)
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
			values = frappe.call(api_path, filters=self.context.filters, periods=self.period_list, row=row)

			if row.reverse_sign:
				values = [-1 * v for v in values]

			# TODO: add support for server script
			# use form_dict to pass input in server script
		except Exception as e:
			frappe.log_error(f"Custom API Error: {api_path} - {e!s}")
			values = [0.0] * len(self.period_list)

		if row.reference_code:
			self.row_values[row.reference_code] = values

		return RowData(row=row, values=values)

	def _process_formula_row(self, row) -> RowData:
		calculator = FormulaCalculator(self.row_values, self.period_list)
		values = calculator.evaluate_formula(row)

		if row.reference_code:
			self.row_values[row.reference_code] = values

		return RowData(row=row, values=values)

	def _process_blank_row(self, row) -> RowData:
		return RowData(row=row, values=[""] * len(self.period_list))

	def _process_column_break_row(self, row) -> RowData:
		return RowData(row=row, values=[])

	def _process_section_break_row(self, row) -> RowData:
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
		result.notify_user()

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

		adj_list = {code: [] for code in formula_row_map}
		in_degree = {code: 0 for code in formula_row_map}

		# Calculate in-degree
		for code in formula_row_map:
			deps = self.dependencies.get(code, [])
			for dep in deps:
				if dep in formula_row_map:  # Only consider dependencies within formula rows
					adj_list[dep].append(code)
					in_degree[code] += 1

		# Topological sort
		queue = [code for code, degree in in_degree.items() if degree == 0]
		result = []

		while queue:
			current = queue.pop(0)
			result.append(formula_row_map[current])

			# Reduce in-degree
			for neighbor in adj_list[current]:
				in_degree[neighbor] -= 1
				if in_degree[neighbor] == 0:
					queue.append(neighbor)

		# Add any remaining formula rows
		result_set = set(result)
		for row in formula_rows:
			if row not in result_set:
				result.append(row)

		return result


class FormulaCalculator:
	"""Enhanced formula calculator with better error handling"""

	def __init__(self, row_data: dict[str, list[float]], period_list: list[dict]):
		self.row_data = row_data
		self.period_list = period_list
		self.precision = get_currency_precision()
		self.validator = CalculationFormulaValidator(set(row_data.keys()))

		self.math_functions = {
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

	def evaluate_formula(self, report_row: dict[str, Any]) -> list[float]:
		validation_result = self.validator.validate(report_row)
		formula = report_row.calculation_formula
		negation_factor = -1 if report_row.reverse_sign else 1

		if validation_result.issues:
			# TODO: Throw?
			messages = "<br><br>".join(issue.message for issue in validation_result.issues)
			frappe.log_error(f"Formula validation errors found:\n{messages}")
			return [0.0] * len(self.period_list)

		results = []
		for i in range(len(self.period_list)):
			result = self._evaluate_for_period(formula, i, negation_factor)
			results.append(result)

		return results

	def _evaluate_for_period(self, formula: str, period_index: int, negation_factor: int) -> float:
		# TODO: consistent error handling
		try:
			context = self._build_context(period_index)
			result = frappe.safe_eval(formula, context)
			return flt(result * negation_factor, self.precision)

		except ZeroDivisionError:
			frappe.log_error(f"Division by zero in formula: {formula}")
			return 0.0
		except Exception as e:
			frappe.log_error(f"Formula evaluation error: {formula} - {e!s}")
			return 0.0

	def _build_context(self, period_index: int) -> dict[str, Any]:
		context = {}

		# row values
		for code, values in self.row_data.items():
			if period_index < len(values):
				context[code] = values[period_index] or 0.0
			else:
				context[code] = 0.0

		# math functions
		context.update(self.math_functions)

		return context


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

		for section in self.organizer.sections:
			for row_index in range(self.organizer.max_rows(section)):
				formatted_row = self.formatter.format_row(section.segments, row_index)
				if formatted_row:  # Always include rows that were formatted
					# Add metadata
					formatted_row["_segment_info"] = {
						"total_segments": len(section.segments),
						"period_keys": [p["key"] for p in self.context.period_list],  # Add period keys
					}
					formatted_data.append(formatted_row)

		return formatted_data

	def _generate_columns(self) -> list[dict]:
		base_columns = get_columns(
			self.context.filters.get("periodicity"),
			self.context.period_list,
			self.context.filters.get("accumulated_values") in (1, None),
			self.context.filters.get("company"),
		)

		return self.formatter.get_columns(self.organizer.section_with_max_segments.segments, base_columns)

	def _expand_segments_with_details(self):
		for section in self.organizer.sections:
			for segment in section.segments:
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
				condition=lambda rd: getattr(rd.row, "warn_if_negative", False),
				format_properties={"warn_if_negative": True},
			),
			FormattingRule(
				condition=lambda rd: getattr(rd.row, "data_source", "") == "Blank Line",
				format_properties={"is_blank_line": True},
			),
			FormattingRule(
				condition=lambda rd: getattr(rd.row, "fieldtype", ""),
				format_properties=lambda rd: {"fieldtype": getattr(rd.row, "fieldtype", "").strip()},
			),
			FormattingRule(
				condition=lambda rd: getattr(rd.row, "color", ""),
				format_properties=lambda rd: {"color": getattr(rd.row, "color", "").strip()},
			),
			FormattingRule(
				condition=lambda rd: getattr(rd.row, "data_source", "") == "Account Data",
				format_properties=lambda rd: {
					"account_filters": getattr(rd.row, "calculation_formula", "").strip()
				},
			),
		]

	def get_formatting(self, row_data: RowData) -> dict[str, Any]:
		formatting = {}
		for rule in self.rules:
			if rule.applies_to(row_data):
				properties = rule.get_properties(row_data)
				formatting.update(properties)

		return formatting


class SegmentOrganizer:
	"""Handles segment organization by `Column Break`, `Section Break` and metadata extraction"""

	def __init__(self, processed_rows: list[RowData]):
		self.sections = self._organize_into_sections(processed_rows)

		# ensure same segment length across sections
		max_segments = self.max_segments
		for section in self.sections:
			if len(section.segments) >= max_segments:
				continue

			# Pad with empty segments
			empty_segments = [SegmentData(index=i) for i in range(len(section.segments), max_segments)]
			section.segments.extend(empty_segments)

	def _organize_into_sections(self, rows: list[RowData]) -> list[SectionData]:
		sections = []
		current_section_rows = []
		section_index = 0
		section_label = ""

		for row_data in rows:
			if not self._should_show_row(row_data):
				continue

			if row_data.row.data_source == "Section Break":
				# Process current section if we have rows
				if current_section_rows:
					section_segments = self._organize_into_segments(current_section_rows, section_label)
					sections.append(
						SectionData(segments=section_segments, label=section_label, index=section_index)
					)
					section_index += 1
					current_section_rows = []

				# Label for the next section
				section_label = getattr(row_data.row, "display_name", "") or ""
			else:
				current_section_rows.append(row_data)

		# Add final section
		if current_section_rows or not sections:
			section_segments = self._organize_into_segments(current_section_rows, section_label)
			sections.append(SectionData(segments=section_segments, label=section_label, index=section_index))

		return sections

	def _organize_into_segments(self, rows: list[RowData], section_label: str) -> list[SegmentData]:
		segments = []
		current_rows = []
		segment_index = 0
		segment_label = ""

		section_header = None
		if section_label:
			section_header = RowData(
				row=frappe._dict(
					{
						"data_source": "Blank Line",
						"display_name": section_label,
						"bold_text": True,
					}
				)
			)

		for row_data in rows:
			if row_data.row.data_source == "Column Break":
				# Save current segment
				if section_header and current_rows:
					current_rows.insert(0, section_header)
					section_header = RowData(row=frappe._dict({"data_source": "Blank Line"}))

				if current_rows:
					segments.append(SegmentData(rows=current_rows, label=segment_label, index=segment_index))
					segment_index += 1
					current_rows = []

				# Label for the next segment
				segment_label = getattr(row_data.row, "display_name", "") or ""
			else:
				current_rows.append(row_data)

		# Add final segment
		if section_header and current_rows:
			current_rows.insert(0, section_header)

		if current_rows or not segments:
			segments.append(SegmentData(rows=current_rows, label=segment_label, index=segment_index))

		return segments

	@property
	def is_single_segment(self) -> bool:
		return self.max_segments == 1

	def max_rows(self, section: SectionData) -> int:
		return max(len(seg.rows) for seg in section.segments) if section.segments else 0

	@property
	def max_segments(self) -> bool:
		return max(len(s.segments) for s in self.sections)

	@property
	def section_with_max_segments(self) -> SectionData:
		return max(self.sections, key=lambda s: len(s.segments))

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
		# TODO: can be commonify COA? @abdeali
		child_accounts = []

		if row_data.account_details:
			child_accounts = list(row_data.account_details.keys())

		values = {
			"child_accounts": child_accounts,
			"account": getattr(row_data.row, "display_name", "") or "",
			"indent": getattr(row_data.row, "indentation_level", 0),
			"account_name": getattr(row_data.row, "account", "") or "",
			"currency": self.context.currency or "",
			"period_start_date": getattr(self.context.filters, "period_start_date", "") or "",
			"period_end_date": getattr(self.context.filters, "period_end_date", "") or "",
			"total": 0,
		}

		for i, period in enumerate(self.period_list):
			period_value = self._get_period_value(row_data, i)
			values[period["key"]] = period_value

			if self.context.filters.get("accumulated_values") == 0:
				values["total"] += flt(period_value)

		# avg for percent
		if self.context.filters.get("accumulated_values") == 0 and row_data.row.fieldtype == "Percent":
			values["total"] = values["total"] / len(self.period_list)

		return values

	def _get_period_value(self, row_data: RowData, period_index: int) -> Any:
		if period_index < len(row_data.values):
			return row_data.values[period_index]

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
		for col in base_columns:
			if col["fieldname"] == "account":
				col["align"] = "left"

		return base_columns


class MultiSegmentFormatter(RowFormatterBase):
	def format_row(self, segments: list[SegmentData], row_index: int) -> dict[str, Any]:
		formatted = {"segment_values": {}}

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
					new_col["align"] = "left"

				if segment.label and col["fieldname"] in [p["key"] for p in self.period_list]:
					new_col["label"] = f"{segment.label} - {col['label']}"

				columns.append(new_col)

		return columns

	def _add_segment_data(self, formatted: dict, row_data: RowData, segment: SegmentData):
		segment_values = self._get_values(row_data)

		for key, value in segment_values.items():
			formatted[f"{segment.id}_{key}"] = value

		formatting = self.formatting_engine.get_formatting(row_data)
		segment_values.update(formatting)

		formatted["segment_values"][segment.id] = segment_values

	def _add_empty_segment(self, formatted: dict, segment: SegmentData):
		formatted[f"account_{segment.id}"] = ""
		for period in self.period_list:
			formatted[f"{segment.id}_{period['key']}"] = ""

		formatted["segment_values"][segment.id] = {"is_blank_line": True}


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
				"fieldtype": getattr(parent_row, "fieldtype", None),
				"bold_text": False,
				"italic_text": True,
				"reverse_sign": getattr(parent_row, "reverse_sign", False),
				"warn_if_negative": getattr(parent_row, "warn_if_negative", False),
				"hide_when_empty": getattr(parent_row, "hide_when_empty", False),
				"hidden_calculation": False,
			},
		)()


class ChartDataGenerator:
	def __init__(self, context: ReportContext):
		self.context = context
		self.processed_rows = context.processed_rows
		self.period_list = context.period_list
		self.filters = context.filters
		self.currency = context.currency

	def generate(self) -> dict[str, Any]:
		chart_rows = [
			row
			for row in self.processed_rows
			if getattr(row.row, "include_in_charts", False)
			and row.row.data_source not in ["Blank Line", "Column Break", "Section Break"]
		]

		if not chart_rows:
			return {}

		labels = [p.get("label") for p in self.period_list]
		datasets = []

		for row_data in chart_rows:
			display_name = getattr(row_data.row, "display_name", "")
			values = []
			for i, _period in enumerate(self.period_list):
				if i < len(row_data.values):
					value = row_data.values[i]
					values.append(flt(value, 2))
				else:
					values.append(0.0)

			# only non-zero values
			if any(v != 0 for v in values):
				datasets.append({"name": display_name, "values": values})

		if not datasets:
			return {}

		# chart config
		if not self.filters.get("accumulated_values") or len(labels) <= 1:
			chart_type = "bar"
		else:
			chart_type = "line"

		self.context.raw_data["chart"] = {
			"data": {"labels": labels, "datasets": datasets},
			"type": chart_type,
			"fieldtype": "Currency",
			"options": "currency",
			"currency": self.currency,
		}


class GrowthViewTransformer:
	def __init__(self, context: ReportContext):
		self.context = context
		self.formatted_rows = context.raw_data.get("formatted_data", [])
		self.period_list = context.period_list

	def transform(self) -> None:
		for row_data in self.formatted_rows:
			if row_data.get("is_blank_line"):
				continue

			transformed_values = {}
			for i in range(len(self.period_list)):
				current_period = self.period_list[i]["key"]

				current_value = row_data[current_period]
				previous_value = row_data[self.period_list[i - 1]["key"]] if i != 0 else 0

				if i == 0:
					transformed_values[current_period] = current_value
				else:
					growth_percent = self._calculate_growth(previous_value, current_value)
					transformed_values[current_period] = growth_percent

			row_data.update(transformed_values)

	def _calculate_growth(self, previous_value: float, current_value: float) -> float | None:
		if current_value is None:
			return None

		if previous_value == 0 and current_value > 0:
			return 100.0
		elif previous_value == 0 and current_value <= 0:
			return 0.0
		else:
			return flt(((current_value - previous_value) / abs(previous_value)) * 100, 2)
