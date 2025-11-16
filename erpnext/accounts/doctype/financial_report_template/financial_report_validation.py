# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import ast
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar

import frappe
from frappe import _
from frappe.database.operator_map import OPERATOR_MAP
from frappe.database.query import SQLFunctionParser


@dataclass
class ValidationIssue:
	"""Represents a single validation issue"""

	message: str
	row_idx: int | None = None
	field: str | None = None
	details: dict[str, Any] = None

	def __post_init__(self):
		if self.details is None:
			self.details = {}

	def __str__(self) -> str:
		prefix = f"Row {self.row_idx}: " if self.row_idx else ""
		field_info = f"[{self.field}] " if self.field else ""
		message = f"{prefix}{field_info}{self.message}"
		return _(message)


@dataclass
class ValidationResult:
	issues: list[ValidationIssue] = field(default_factory=list)
	warnings: list[ValidationIssue] = field(default_factory=list)

	@property
	def is_valid(self) -> bool:
		return len(self.issues) == 0

	@property
	def has_warnings(self) -> bool:
		return len(self.warnings) > 0

	@property
	def error_count(self) -> int:
		return len(self.issues)

	@property
	def warning_count(self) -> int:
		return len(self.warnings)

	def merge(self, other: "ValidationResult") -> "ValidationResult":
		self.issues.extend(other.issues)
		self.warnings.extend(other.warnings)
		return self

	def add_error(self, issue: ValidationIssue) -> None:
		"""Add a critical error that prevents functionality"""
		self.issues.append(issue)

	def add_warning(self, issue: ValidationIssue) -> None:
		"""Add a warning for recommendatory validation"""
		self.warnings.append(issue)

	def notify_user(self) -> None:
		warnings = "<br><br>".join(str(w) for w in self.warnings)
		errors = "<br><br>".join(str(e) for e in self.issues)

		if warnings:
			frappe.msgprint(warnings, title=_("Warnings"), indicator="orange")

		if errors:
			frappe.throw(errors, title=_("Errors"))


class TemplateValidator:
	"""Main validator that orchestrates all validations"""

	def __init__(self, template):
		self.template = template
		self.validators = [
			TemplateStructureValidator(),
			DependencyValidator(template),
		]
		self.formula_validator = FormulaValidator(template)

	def validate(self) -> ValidationResult:
		result = ValidationResult([])

		# Run template-level validators
		for validator in self.validators:
			result.merge(validator.validate(self.template))

		# Run row-level validations
		account_fields = {field.fieldname for field in frappe.get_meta("Account").fields}
		for row in self.template.rows:
			result.merge(self.formula_validator.validate(row, account_fields))

		return result


class Validator(ABC):
	@abstractmethod
	def validate(self, context: Any) -> ValidationResult:
		pass


class TemplateStructureValidator(Validator):
	def validate(self, template) -> ValidationResult:
		result = ValidationResult()

		result.merge(self._validate_reference_codes(template))
		result.merge(self._validate_required_fields(template))

		return result

	def _validate_reference_codes(self, template) -> ValidationResult:
		result = ValidationResult()
		used_codes = set()

		for row in template.rows:
			if not row.reference_code:
				continue

			ref_code = row.reference_code.strip()

			# Check format
			if not re.match(r"^[A-Za-z][A-Za-z0-9_-]*$", ref_code):
				result.add_error(
					ValidationIssue(
						message=f"Invalid line reference format: '{ref_code}'. Must start with letter and contain only letters, numbers, underscores, and hyphens",
						row_idx=row.idx,
					)
				)

			# Check uniqueness
			if ref_code in used_codes:
				result.add_error(
					ValidationIssue(
						message=f"Duplicate line reference: '{ref_code}'",
						row_idx=row.idx,
					)
				)
			used_codes.add(ref_code)

		return result

	def _validate_required_fields(self, template) -> ValidationResult:
		result = ValidationResult()

		for row in template.rows:
			# Balance type required
			if row.data_source == "Account Data" and not row.balance_type:
				result.add_error(
					ValidationIssue(
						message="Balance Type is required for Account Data",
						row_idx=row.idx,
					)
				)

			# Calculation formula required
			if row.data_source in ["Account Data", "Calculated Amount", "Custom API"]:
				if not row.calculation_formula:
					result.add_error(
						ValidationIssue(
							message=f"Formula is required for {row.data_source}",
							row_idx=row.idx,
						)
					)

		return result


class DependencyValidator(Validator):
	def __init__(self, template):
		self.template = template
		self.dependencies = self._build_dependency_graph()

	def validate(self, context=None) -> ValidationResult:
		result = ValidationResult()

		result.merge(self._validate_circular_dependencies())
		result.merge(self._validate_missing_dependencies())

		return result

	def _build_dependency_graph(self) -> dict[str, list[str]]:
		graph = {}
		available_codes = {row.reference_code for row in self.template.rows if row.reference_code}

		for row in self.template.rows:
			if row.reference_code and row.data_source == "Calculated Amount" and row.calculation_formula:
				deps = extract_reference_codes_from_formula(row.calculation_formula, list(available_codes))
				if deps:
					graph[row.reference_code] = deps

		return graph

	def _validate_circular_dependencies(self) -> ValidationResult:
		"""
		Efficient cycle detection using DFS (Depth-First Search) with three-color algorithm:
		- WHITE (0): unvisited node
		- GRAY (1): currently being processed (on recursion stack)
		- BLACK (2): fully processed

		Example cycle detection:
		A → B → C → A (cycle detected when A is GRAY and visited again)
		"""
		result = ValidationResult()
		WHITE, GRAY, BLACK = 0, 1, 2
		colors = {node: WHITE for node in self.dependencies}

		def dfs(node, path):
			if node not in colors:
				return  # External dependency

			if colors[node] == GRAY:
				# Found cycle
				cycle_start = path.index(node)
				cycle = [*path[cycle_start:], node]
				result.add_error(
					ValidationIssue(
						message=f"Circular dependency detected: {' → '.join(cycle)}",
					)
				)
				return

			if colors[node] == BLACK:
				return  # Already processed

			colors[node] = GRAY
			path.append(node)

			for neighbor in self.dependencies.get(node, []):
				dfs(neighbor, path.copy())

			colors[node] = BLACK

		for node in self.dependencies:
			if colors[node] == WHITE:
				dfs(node, [])

		return result

	def _validate_missing_dependencies(self) -> ValidationResult:
		available = {row.reference_code for row in self.template.rows if row.reference_code}
		result = ValidationResult()

		for ref_code, deps in self.dependencies.items():
			undefined = [d for d in deps if d not in available]
			if undefined:
				row_idx = self._get_row_idx(ref_code)
				result.add_error(
					ValidationIssue(
						message=f"Line References undefined in Formula: {', '.join(undefined)}",
						row_idx=row_idx,
					)
				)

		return result

	def _get_row_idx(self, reference_code: str) -> int | None:
		for row in self.template.rows:
			if row.reference_code == reference_code:
				return row.idx
		return None


class CalculationFormulaValidator(Validator):
	"""Validates calculation formulas used in Calculated Amount rows"""

	def __init__(self, reference_codes: set[str]):
		self.reference_codes = reference_codes

	def validate(self, row) -> ValidationResult:
		"""Validate calculation formula for a single row"""
		result = ValidationResult()

		if row.data_source != "Calculated Amount":
			return result

		if not row.calculation_formula:
			result.add_error(
				ValidationIssue(
					message="Formula is required for Calculated Amount",
					row_idx=row.idx,
					field="Formula",
				)
			)
			return result

		formula = self._preprocess_formula(row.calculation_formula)
		row.calculation_formula = formula

		# Check parentheses
		if not self._are_parentheses_balanced(formula):
			result.add_error(
				ValidationIssue(
					message="Formula has unbalanced parentheses",
					row_idx=row.idx,
				)
			)
			return result

		# Check self-reference
		available_codes = list(self.reference_codes)
		refs = extract_reference_codes_from_formula(formula, available_codes)
		if row.reference_code and row.reference_code in refs:
			result.add_error(
				ValidationIssue(
					message=f"Formula references itself ('{row.reference_code}')",
					row_idx=row.idx,
				)
			)

		# Check undefined references
		undefined = set(refs) - set(available_codes)
		if undefined:
			result.add_error(
				ValidationIssue(
					message=f"Formula references undefined codes: {', '.join(undefined)}",
					row_idx=row.idx,
				)
			)

		# Try to evaluate with dummy values
		eval_error = self._test_formula_evaluation(formula, available_codes)
		if eval_error:
			result.add_error(
				ValidationIssue(
					message=f"Formula evaluation error: {eval_error}",
					row_idx=row.idx,
				)
			)

		return result

	def _preprocess_formula(self, formula: str) -> str:
		if not formula or not isinstance(formula, str):
			return ""

		return formula.strip()

	@staticmethod
	def _are_parentheses_balanced(formula: str) -> bool:
		return formula.count("(") == formula.count(")")

	def _test_formula_evaluation(self, formula: str, available_codes: list[str]) -> str | None:
		try:
			context = {code: 1.0 for code in available_codes}
			context.update(
				{
					"abs": abs,
					"round": round,
					"min": min,
					"max": max,
					"sum": sum,
					"sqrt": lambda x: x**0.5,
					"pow": pow,
					"ceil": lambda x: int(x) + (1 if x % 1 else 0),
					"floor": lambda x: int(x),
				}
			)

			result = frappe.safe_eval(formula, eval_globals=None, eval_locals=context)

			if not isinstance(result, (int, float)):  # noqa: UP038
				return f"Formula must return a numeric value, got {type(result).__name__}"

			return None
		except Exception as e:
			return str(e)


class AccountFilterValidator(Validator):
	"""Validates account filter expressions used in Account Data rows"""

	def __init__(self, account_fields: set | None = None):
		self.account_fields = account_fields or set(frappe.get_meta("Account")._valid_columns)

	def validate(self, row) -> ValidationResult:
		result = ValidationResult()

		if row.data_source != "Account Data":
			return result

		if not row.calculation_formula:
			result.add_error(
				ValidationIssue(
					message="Account filter is required for Account Data",
					row_idx=row.idx,
					field="Formula",
				)
			)
			return result

		try:
			filter_config = json.loads(row.calculation_formula)
			error = self._validate_filter_structure(filter_config, self.account_fields)

			if error:
				result.add_error(
					ValidationIssue(
						message=error,
						row_idx=row.idx,
						field="Account Filter",
					)
				)

		except json.JSONDecodeError as e:
			result.add_error(
				ValidationIssue(
					message=f"Invalid JSON format: {e!s}",
					row_idx=row.idx,
					field="Account Filter",
				)
			)

		return result

	def _validate_filter_structure(self, filter_config, account_fields: set) -> str | None:
		# simple condition: [field, operator, value]
		if isinstance(filter_config, list):
			if len(filter_config) != 3:
				return "Filter must be [field, operator, value]"

			field, operator, value = filter_config

			if not isinstance(field, str) or not isinstance(operator, str):
				return "Field and operator must be strings"

			if field not in account_fields:
				return f"Field '{field}' is not a valid account field"

			if operator.casefold() not in OPERATOR_MAP:
				return f"Invalid operator '{operator}'"

			if operator in ["in", "not in"] and not isinstance(value, list):
				return f"Operator '{operator}' requires a list value"

		# logical condition: {"and": [condition1, condition2]}
		elif isinstance(filter_config, dict):
			if len(filter_config) != 1:
				return "Logical condition must have exactly one operator"

			op = next(iter(filter_config.keys())).lower()
			if op not in ["and", "or"]:
				return "Logical operators must be 'and' or 'or'"

			conditions = filter_config[next(iter(filter_config.keys()))]
			if not isinstance(conditions, list) or len(conditions) < 1:
				return "Logical conditions need at least 1 sub-condition"

			# recursive
			for condition in conditions:
				error = self._validate_filter_structure(condition, account_fields)
				if error:
					return error
		else:
			return "Filter must be a list or dict"

		return None


class FormulaValidator(Validator):
	def __init__(self, template):
		self.template = template
		reference_codes = {row.reference_code for row in template.rows if row.reference_code}
		self.calculation_validator = CalculationFormulaValidator(reference_codes)
		self.account_filter_validator = AccountFilterValidator()

	def validate(self, row, account_fields: set) -> ValidationResult:
		result = ValidationResult()

		if not row.calculation_formula:
			return result

		if row.data_source == "Calculated Amount":
			return self.calculation_validator.validate(row)

		elif row.data_source == "Account Data":
			# Update account fields if provided
			if account_fields:
				self.account_filter_validator.account_fields = account_fields
			return self.account_filter_validator.validate(row)

		elif row.data_source == "Custom API":
			result.merge(self._validate_custom_api(row))

		return result

	def _validate_custom_api(self, row) -> ValidationResult:
		result = ValidationResult()
		api_path = row.calculation_formula

		if "." not in api_path:
			result.add_error(
				ValidationIssue(
					message="Custom API path should be in format: app.module.method",
					row_idx=row.idx,
					field="Formula",
				)
			)
			return result

		# Method exists?
		try:
			module_path, method_name = api_path.rsplit(".", 1)
			module = frappe.get_module(module_path)

			if not hasattr(module, method_name):
				result.add_error(
					ValidationIssue(
						message=f"Method '{method_name}' not found in module '{module_path}' (might be environment-specific)",
						row_idx=row.idx,
						field="Formula",
					)
				)
		except Exception as e:
			result.add_error(
				ValidationIssue(
					message=f"Could not validate API path: {e!s}",
					row_idx=row.idx,
					field="Formula",
				)
			)

		return result


def extract_reference_codes_from_formula(formula: str, available_codes: list[str]) -> list[str]:
	found_codes = []
	for code in available_codes:
		# Match complete words only to avoid partial matches
		pattern = r"\b" + re.escape(code) + r"\b"
		if re.search(pattern, formula):
			found_codes.append(code)
	return found_codes
