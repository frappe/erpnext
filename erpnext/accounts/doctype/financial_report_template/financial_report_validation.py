# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar

import frappe
from frappe import _


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
	"""Result of validation containing all issues"""

	issues: list[ValidationIssue] = field(default_factory=list)

	@property
	def is_valid(self) -> bool:
		return len(self.issues) == 0

	def merge(self, other: "ValidationResult") -> "ValidationResult":
		self.issues.extend(other.issues)
		return self


class TemplateValidator:
	"""Main validator that orchestrates all validations"""

	def __init__(self, template):
		self.template = template
		self.validators = [
			StandardTemplateValidator(),
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
		for row in self.template.rows:
			result.merge(self.formula_validator.validate(row))

		return result

	def get_error_messages(self) -> list[str]:
		result = self.validate()
		return [str(issue) for issue in result.issues]


class Validator(ABC):
	@abstractmethod
	def validate(self, context: Any) -> ValidationResult:
		pass


class StandardTemplateValidator(Validator):
	PROTECTED_FIELDS: ClassVar[list[str]] = ["template_name", "report_type", "module"]

	def validate(self, template) -> ValidationResult:
		issues = []

		if not template.is_standard or not hasattr(template, "_doc_before_save"):
			return ValidationResult(issues)

		if not template._doc_before_save or not template._doc_before_save.is_standard:
			return ValidationResult(issues)

		for field_name in self.PROTECTED_FIELDS:
			if template.get(field_name) != template._doc_before_save.get(field_name):
				issues.append(
					ValidationIssue(
						message=f"Cannot modify {field_name.replace('_', ' ').title()} in standard template",
					)
				)

		return ValidationResult(issues)


class TemplateStructureValidator(Validator):
	def validate(self, template) -> ValidationResult:
		issues = []

		issues.extend(self._validate_reference_codes(template))

		issues.extend(self._validate_required_fields(template))

		issues.extend(self._validate_orphaned_references(template))

		return ValidationResult(issues)

	def _validate_reference_codes(self, template) -> list[ValidationIssue]:
		issues = []
		used_codes = set()

		for row in template.rows:
			if not row.reference_code:
				continue

			ref_code = row.reference_code.strip()

			# Check format
			if not re.match(r"^[A-Za-z][A-Za-z0-9_-]*$", ref_code):
				issues.append(
					ValidationIssue(
						message=f"Invalid line reference format: '{ref_code}'. Must start with letter and contain only letters, numbers, underscores, and hyphens",
						row_idx=row.idx,
					)
				)

			# Check uniqueness
			if ref_code in used_codes:
				issues.append(
					ValidationIssue(
						message=f"Duplicate line reference: '{ref_code}'",
						row_idx=row.idx,
					)
				)
			used_codes.add(ref_code)

		return issues

	def _validate_required_fields(self, template) -> list[ValidationIssue]:
		issues = []

		for row in template.rows:
			# Balance type required
			if row.data_source == "Account Data" and not row.balance_type:
				issues.append(
					ValidationIssue(
						message="Balance Type is required for Account Data",
						row_idx=row.idx,
					)
				)

			# Calculation formula required
			if row.data_source in ["Account Data", "Calculated Amount", "Custom API"]:
				if not row.calculation_formula:
					issues.append(
						ValidationIssue(
							message=f"Formula is required for {row.data_source}",
							row_idx=row.idx,
						)
					)

		return issues

	def _validate_orphaned_references(self, template) -> list[ValidationIssue]:
		issues = []
		all_refs = {row.reference_code for row in template.rows if row.reference_code}
		used_refs = set()

		for row in template.rows:
			if row.calculation_formula and row.data_source == "Calculated Amount":
				used_refs.update(
					extract_reference_codes_from_formula(row.calculation_formula, list(all_refs))
				)

		orphaned = all_refs - used_refs
		if orphaned:
			# TODO: could be a message print instead of throw
			issues.append(
				ValidationIssue(
					message=f"Orphaned Line Reference (not used in any formula): {', '.join(orphaned)}",
				)
			)

		return issues


class DependencyValidator(Validator):
	def __init__(self, template):
		self.template = template
		self.dependencies = self._build_dependency_graph()

	def validate(self, context=None) -> ValidationResult:
		issues = []

		issues.extend(self._validate_circular_dependencies())

		issues.extend(self._validate_missing_dependencies())

		return ValidationResult(issues)

	def _build_dependency_graph(self) -> dict[str, list[str]]:
		graph = {}
		available_codes = {row.reference_code for row in self.template.rows if row.reference_code}

		for row in self.template.rows:
			if row.reference_code and row.data_source == "Calculated Amount" and row.calculation_formula:
				deps = extract_reference_codes_from_formula(row.calculation_formula, list(available_codes))
				if deps:
					graph[row.reference_code] = deps

		return graph

	def _validate_circular_dependencies(self) -> list[ValidationIssue]:
		"""
		Efficient cycle detection using DFS (Depth-First Search) with three-color algorithm:
		- WHITE (0): unvisited node
		- GRAY (1): currently being processed (on recursion stack)
		- BLACK (2): fully processed

		Example cycle detection:
		A → B → C → A (cycle detected when A is GRAY and visited again)
		"""
		WHITE, GRAY, BLACK = 0, 1, 2
		colors = {node: WHITE for node in self.dependencies}
		cycles = []

		def dfs(node, path):
			if node not in colors:
				return  # External dependency

			if colors[node] == GRAY:
				# Found cycle
				cycle_start = path.index(node)
				cycle = [*path[cycle_start:], node]
				cycles.append(
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

		return cycles

	def _validate_missing_dependencies(self) -> list[ValidationIssue]:
		available = {row.reference_code for row in self.template.rows if row.reference_code}

		issues = []
		for ref_code, deps in self.dependencies.items():
			undefined = [d for d in deps if d not in available]
			if undefined:
				row_idx = self._get_row_idx(ref_code)
				issues.append(
					ValidationIssue(
						message=f"Line References undefined in Formula: {', '.join(undefined)}",
						row_idx=row_idx,
					)
				)

		return issues

	def _get_row_idx(self, reference_code: str) -> int | None:
		for row in self.template.rows:
			if row.reference_code == reference_code:
				return row.idx
		return None


class FormulaValidator(Validator):
	def __init__(self, template):
		self.template = template
		self.rows_by_code = {row.reference_code: row for row in template.rows if row.reference_code}

	def validate(self, row) -> ValidationResult:
		issues = []

		if not row.calculation_formula:
			return ValidationResult(issues)

		if row.data_source == "Calculated Amount":
			issues.extend(self._validate_calculated_formula(row))
		elif row.data_source == "Account Data":
			issues.extend(self._validate_account_filter(row))
		elif row.data_source == "Custom API":
			issues.extend(self._validate_custom_api(row))

		return ValidationResult(issues)

	def _validate_calculated_formula(self, row) -> list[ValidationIssue]:
		issues = []
		formula = row.calculation_formula

		# Check parentheses
		if not self._are_parentheses_balanced(formula):
			issues.append(
				ValidationIssue(
					message="Formula has unbalanced parentheses",
					row_idx=row.idx,
				)
			)
			return issues  # Can't validate further

		# Check self-reference
		available_codes = list(self.rows_by_code.keys())
		refs = extract_reference_codes_from_formula(formula, available_codes)
		if row.reference_code and row.reference_code in refs:
			issues.append(
				ValidationIssue(
					message=f"Formula references itself ('{row.reference_code}')",
					row_idx=row.idx,
				)
			)

		# Check undefined references
		undefined = set(refs) - set(available_codes)
		if undefined:
			issues.append(
				ValidationIssue(
					message=f"Formula references undefined codes: {', '.join(undefined)}",
					row_idx=row.idx,
				)
			)

		# Try to evaluate with dummy values
		eval_error = self._test_formula_evaluation(formula, available_codes)
		if eval_error:
			issues.append(
				ValidationIssue(
					message=f"Formula evaluation error: {eval_error}",
					row_idx=row.idx,
				)
			)

		return issues

	def _validate_account_filter(self, row) -> list[ValidationIssue]:
		try:
			filter_config = json.loads(row.calculation_formula)
			error = self._validate_filter_structure(filter_config)

			if error:
				return [
					ValidationIssue(
						message=error,
						row_idx=row.idx,
						field="Account Filter",
					)
				]
		except json.JSONDecodeError as e:
			return [
				ValidationIssue(
					message=f"Invalid JSON format: {e!s}",
					row_idx=row.idx,
					field="Account Filter",
				)
			]

		return []

	def _validate_filter_structure(self, filter_config) -> str | None:
		if isinstance(filter_config, list):
			if len(filter_config) != 3:
				return "Filter must be [field, operator, value]"

			field, operator, value = filter_config
			if not isinstance(field, str) or not isinstance(operator, str):
				return "Field and operator must be strings"

			valid_ops = ["=", "!=", "in", "not in", "like", ">", ">=", "<", "<="]
			if operator not in valid_ops:
				return f"Invalid operator '{operator}'"

			if operator in ["in", "not in"] and not isinstance(value, list):
				return f"Operator '{operator}' requires a list value"

		elif isinstance(filter_config, dict):
			if len(filter_config) != 1:
				return "Logical condition must have exactly one operator"

			op = next(iter(filter_config.keys())).lower()
			if op not in ["and", "or"]:
				return "Logical operators must be 'and' or 'or'"

			conditions = filter_config[next(iter(filter_config.keys()))]
			if not isinstance(conditions, list) or len(conditions) < 2:
				return "Logical conditions need at least 2 sub-conditions"

			for condition in conditions:
				error = self._validate_filter_structure(condition)
				if error:
					return error
		else:
			return "Filter must be a list or dict"

		return None

	def _validate_custom_api(self, row) -> list[ValidationIssue]:
		api_path = row.calculation_formula

		if "." not in api_path:
			return [
				ValidationIssue(
					message="Custom API path should be in format: app.module.method",
					row_idx=row.idx,
					field="Formula",
				)
			]

		# Method exists?
		try:
			module_path, method_name = api_path.rsplit(".", 1)
			module = frappe.get_module(module_path)

			if not hasattr(module, method_name):
				return [
					ValidationIssue(
						message=f"Method '{method_name}' not found in module '{module_path}'",
						row_idx=row.idx,
						field="Formula",
					)
				]
		except Exception as e:
			return [
				ValidationIssue(
					message=f"Could not validate API path: {e!s}",
					row_idx=row.idx,
					field="Formula",
				)
			]

		return []

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

			if not isinstance(result, int | float):
				return f"Formula must return a numeric value, got {type(result).__name__}"

			return None
		except Exception as e:
			return str(e)


def extract_reference_codes_from_formula(formula: str, available_codes: list[str]) -> list[str]:
	found_codes = []
	for code in available_codes:
		# Match complete words only to avoid partial matches
		pattern = r"\b" + re.escape(code) + r"\b"
		if re.search(pattern, formula):
			found_codes.append(code)
	return found_codes
