# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import ast
import json
import keyword
import math
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import frappe
from frappe import _, is_whitelisted
from frappe.database.operator_map import OPERATOR_MAP
from frappe.utils import escape_html
from frappe.utils.safe_exec import WHITELISTED_SAFE_EVAL_GLOBALS

FORMULA_FUNCTIONS = {
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

# Some inbuilt functions that are allowed in formulas.
ALLOWED_FUNCTIONS = frozenset(FORMULA_FUNCTIONS) | frozenset(
	name for name in WHITELISTED_SAFE_EVAL_GLOBALS if not name.startswith("_")
)

# These nodes are not supported by Frappe's safe_eval, so they are not allowed in formulas.
UNSUPPORTED_NODES = (ast.NamedExpr, ast.Lambda)


def get_valid_api_method(api_path: str):
	"""Resolve `api_path`, ensuring it is whitelisted and permits GET (i.e. read-only)."""
	method = frappe.get_attr(api_path)
	is_whitelisted(method)

	if "GET" not in frappe.allowed_http_methods_for_whitelisted_func.get(method, ()):
		frappe.throw(
			_("Method {0} must permit GET requests").format(frappe.bold(api_path)),
			frappe.PermissionError,
			title=_("Method Not Allowed"),
		)

	return method


def get_formula_field_label(data_source: str) -> str:
	# Must mirror the `labels` map in financial_report_template.js (update_formula_label),
	labels = {
		"Account Data": _("Account Filter"),
		"Custom API": _("API Method Path"),
	}
	return labels.get(data_source, _("Calculation Formula"))


@dataclass
class ValidationIssue:
	"""Represents a single validation issue"""

	message: str
	row_idx: int | None = None
	details: dict[str, Any] = None

	def __post_init__(self):
		if self.details is None:
			self.details = {}

	def __str__(self) -> str:
		if self.row_idx:
			return _("Row {0}: {1}", context="Financial Report Template").format(self.row_idx, self.message)
		return self.message


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
		# messages quote user input back, and both are rendered as HTML
		warnings = "<br><br>".join(escape_html(str(w)) for w in self.warnings if w)
		errors = "<br><br>".join(escape_html(str(e)) for e in self.issues if e)

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
		for row in self.template.rows:
			result.merge(self.formula_validator.validate(row))

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

			ref_code = row.reference_code

			# a line reference is used as a name in formulas, so it must be a usable one
			if not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", ref_code):
				result.add_error(
					ValidationIssue(
						message=_(
							"Invalid line reference format: '{0}'. Must start with a letter and contain only letters, numbers and underscores"
						).format(ref_code),
						row_idx=row.idx,
					)
				)
			elif keyword.iskeyword(ref_code) or ref_code in FORMULA_FUNCTIONS:
				result.add_error(
					ValidationIssue(
						message=_("'{0}' is a reserved name and cannot be used as a line reference").format(
							ref_code
						),
						row_idx=row.idx,
					)
				)

			# Check uniqueness
			if ref_code in used_codes:
				result.add_error(
					ValidationIssue(
						message=_("Duplicate line reference: '{0}'").format(ref_code),
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
						message=_("Balance Type is required for Account Data"),
						row_idx=row.idx,
					)
				)

			# Calculation formula required
			if row.data_source in ["Account Data", "Calculated Amount", "Custom API"]:
				if not row.calculation_formula:
					result.add_error(
						ValidationIssue(
							message=_("{0} is required when {1} is {2}").format(
								get_formula_field_label(row.data_source),
								row.meta.get_translated_label("data_source"),
								_(row.data_source),
							),
							row_idx=row.idx,
						)
					)

		return result


class DependencyValidator(Validator):
	def __init__(self, template):
		self.template = template
		self.dependencies = self._build_dependency_graph()

	def validate(self, context=None) -> ValidationResult:
		return self._validate_circular_dependencies()

	def _build_dependency_graph(self) -> dict[str, list[str]]:
		graph = {}
		available_codes = {row.reference_code for row in self.template.rows if row.reference_code}

		for row in self.template.rows:
			if row.reference_code and row.data_source == "Calculated Amount" and row.calculation_formula:
				# skip self-reference, `CalculationFormulaValidator` already reports it
				deps = [
					code
					for code in extract_reference_codes_from_formula(row.calculation_formula, available_codes)
					if code != row.reference_code
				]
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
						message=_("Circular dependency detected: {0}").format(" → ".join(cycle)),
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


class CalculationFormulaValidator(Validator):
	"""Validates calculation formulas used in Calculated Amount rows"""

	def __init__(self, reference_codes: set[str], strict: bool = True):
		"""
		Args:
		        reference_codes: line references the formula may use.
		        strict: report an unknown name as an error instead of a warning.
		"""
		self.reference_codes = reference_codes
		self.strict = strict

	def validate(self, row) -> ValidationResult:
		"""Validate calculation formula for a single row"""
		result = ValidationResult()

		if row.data_source != "Calculated Amount":
			return result

		formula = (row.calculation_formula or "").strip()

		if not formula:
			return result

		try:
			tree = ast.parse(formula, mode="eval")
		except SyntaxError as e:
			result.add_error(
				ValidationIssue(
					# e.msg, not str(e): str would add "(<unknown>, line 1)"
					message=_("Formula has invalid syntax: {0}").format(e.msg),
					row_idx=row.idx,
				)
			)
			return result
		except RecursionError:
			# too deeply nested for the parser to walk
			result.add_error(ValidationIssue(message=_("Formula is too complex"), row_idx=row.idx))
			return result

		if unsupported := self._unsupported_reason(tree, formula):
			result.add_error(
				ValidationIssue(
					message=_("Formula is not allowed: {0}").format(unsupported),
					row_idx=row.idx,
				)
			)
			return result

		result.merge(self._validate_formula_names(tree, row))

		return result

	def _unsupported_reason(self, tree: ast.Expression, formula: str) -> str | None:
		from frappe.utils.safe_exec import FrappeTransformer
		from RestrictedPython import compile_restricted

		# replicating the check in `safe_eval`
		if any(isinstance(node, UNSUPPORTED_NODES) for node in ast.walk(tree)):
			return _("assignment expressions and lambdas are not supported")

		try:
			# check if this formula can be compiled under frappe's restricted rules
			compile_restricted(formula, filename="<formula>", policy=FrappeTransformer, mode="eval")
		except SyntaxError as e:
			# compile_restricted puts a list of reasons in args[0], so str(e) would show
			# the brackets and quotes of a tuple.
			reasons = e.args[0] if e.args else None
			if isinstance(reasons, list | tuple):
				return "; ".join(str(r) for r in reasons)
			return str(reasons or e)
		except RecursionError:
			return _("it is too deeply nested")
		except Exception as e:
			return str(e)

	def _validate_formula_names(self, tree: ast.Expression, row) -> ValidationResult:
		"""
		Validate the names a formula uses against the known codes and functions.

		- Unknown names are reported according to `strict`.
		- A self-reference is always an error: it evaluates without failing and produces a misleading value.
		"""
		result = ValidationResult()
		unknown_functions, unknown_codes, used_codes = self._resolve_names(tree)
		report = result.add_error if self.strict else result.add_warning

		if unknown_functions:
			report(
				ValidationIssue(
					message=_("Formula uses unknown functions: {0}").format(
						", ".join(sorted(unknown_functions))
					),
					row_idx=row.idx,
				)
			)

		if unknown_codes:
			report(
				ValidationIssue(
					message=_("Formula references undefined codes: {0}").format(
						", ".join(sorted(unknown_codes))
					),
					row_idx=row.idx,
				)
			)

		# Always an error. An unknown name raises at run time and the row shows zero, but a
		# self-reference reads the row's own earlier value and prints a plausible wrong number.
		if row.reference_code and row.reference_code in used_codes:
			result.add_error(
				ValidationIssue(
					message=_("Formula references itself ('{0}')").format(row.reference_code),
					row_idx=row.idx,
				)
			)

		return result

	def _resolve_names(self, tree: ast.Expression) -> tuple[set, set, set]:
		"""
		Look up every name a formula uses against the known codes and functions.

		Returns:
		        Unknown functions, unknown codes, and known codes the formula reads.
		"""
		called = {
			node.func.id
			for node in ast.walk(tree)
			if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
		}

		# Names the formula creates itself, such as a loop variable in [x for x in ...].
		# Python marks those as Store; everything read from the context is Load.
		created = {
			node.id
			for node in ast.walk(tree)
			if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
		}

		unknown_functions, unknown_codes, used_codes = set(), set(), set()

		for node in ast.walk(tree):
			if not isinstance(node, ast.Name) or node.id in created:
				continue

			if node.id in called:
				if node.id not in ALLOWED_FUNCTIONS:
					unknown_functions.add(node.id)
			elif node.id in self.reference_codes:
				used_codes.add(node.id)
			elif node.id not in ALLOWED_FUNCTIONS:
				unknown_codes.add(node.id)

		return unknown_functions, unknown_codes, used_codes


class AccountFilterValidator(Validator):
	"""Validates account filter expressions used in Account Data rows"""

	def __init__(self, account_fields: set | None = None):
		self.account_meta = frappe.get_meta("Account")
		self.account_fields = account_fields or set(self.account_meta._valid_columns)

	def validate(self, row) -> ValidationResult:
		# dispatch-path guard: only account-data rows are validated here
		if row.data_source != "Account Data":
			return ValidationResult()

		return self.validate_filter(row)

	def validate_filter(self, row) -> ValidationResult:
		"""Validate calculation_formula as an Account filter, regardless of data_source.

		The caller has already decided this row is an account filter, so unlike
		`validate()` this does not opt out based on `data_source`.
		"""
		result = ValidationResult()

		try:
			filter_config = json.loads(row.calculation_formula)
			error = self._validate_filter_structure(
				filter_config,
				self.account_fields,
				row.advanced_filtering,
			)

			if error:
				result.add_error(
					ValidationIssue(
						message=_("[{0}] {1}", context="Financial Report Template").format(
							get_formula_field_label("Account Data"), error
						),
						row_idx=row.idx,
					)
				)

		except json.JSONDecodeError as e:
			result.add_error(
				ValidationIssue(
					message=_("[{0}] {1}", context="Financial Report Template").format(
						get_formula_field_label("Account Data"),
						_("Invalid JSON format: {0}").format(str(e)),
					),
					row_idx=row.idx,
				)
			)

		return result

	def _validate_filter_structure(
		self,
		filter_config,
		account_fields: set,
		advanced_filtering: bool = False,
	) -> str | None:
		# simple condition: [field, operator, value]
		if isinstance(filter_config, list):
			if len(filter_config) != 3:
				return _("Filter must be [field, operator, value]")

			field, operator, value = filter_config

			if not isinstance(field, str) or not isinstance(operator, str):
				return _("Field and operator must be strings")

			if field not in account_fields:
				return _("Field '{0}' is not a valid Account field").format(field)

			normalized_operator = operator.casefold()

			if normalized_operator not in OPERATOR_MAP:
				return _("Invalid operator '{0}'").format(operator)

			if normalized_operator in ["in", "not in"] and not isinstance(value, list):
				return _("Operator '{0}' requires a list value").format(operator)

		# logical condition: {"and": [condition1, condition2]}
		elif isinstance(filter_config, dict):
			if len(filter_config) != 1:
				return _("Logical condition must have exactly one operator")

			op = next(iter(filter_config.keys())).lower()
			if op not in ["and", "or"]:
				return _("Logical operators must be 'and' or 'or'")

			conditions = filter_config[next(iter(filter_config.keys()))]
			if not isinstance(conditions, list) or len(conditions) < 1:
				return _("Logical conditions need at least 1 sub-condition")

			# recursive
			for condition in conditions:
				error = self._validate_filter_structure(condition, account_fields, advanced_filtering)
				if error:
					return error
		else:
			return _("Filter must be a list or dict")

		return None


class FormulaValidator(Validator):
	def __init__(self, template):
		self.template = template
		reference_codes = {row.reference_code for row in template.rows if row.reference_code}
		self.calculation_validator = CalculationFormulaValidator(reference_codes)
		self.account_filter_validator = AccountFilterValidator()

	def validate(self, row) -> ValidationResult:
		result = ValidationResult()

		if not row.calculation_formula:
			return result

		if row.data_source == "Calculated Amount":
			return self.calculation_validator.validate(row)

		elif row.data_source == "Account Data":
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
					message=_("{0} should be in format: app.module.method").format(
						get_formula_field_label(row.data_source)
					),
					row_idx=row.idx,
				)
			)
			return result

		try:
			get_valid_api_method(api_path)
		except Exception as e:
			if isinstance(e, frappe.PermissionError | frappe.ValidationError):
				# frappe.throw inside get_valid_api_method logs a message that would pop up in UI
				frappe.clear_last_message()

			if isinstance(e, frappe.PermissionError):
				message = _("[{0}] {1}", context="Financial Report Template").format(
					get_formula_field_label(row.data_source),
					_("Method '{0}' must be whitelisted and permit GET requests").format(api_path),
				)
			else:
				message = _("Could not validate {0}: {1}").format(
					get_formula_field_label(row.data_source), str(e)
				)

			result.add_error(ValidationIssue(message=message, row_idx=row.idx))

		return result


def extract_reference_codes_from_formula(formula: str, available_codes: set[str]) -> list[str]:
	"""Return the reference codes a formula depends on, sorted so the result is stable."""
	if not formula:
		return []

	try:
		tree = ast.parse(formula, mode="eval")
	except SyntaxError:
		# An unparseable formula is reported by CalculationFormulaValidator. Fall back to
		# a word match so dependency ordering still sees the codes it can recognise.
		found = {code for code in available_codes if re.search(r"\b" + re.escape(code) + r"\b", formula)}
	else:
		called_names = {
			node.func.id
			for node in ast.walk(tree)
			if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
		}
		# Skip names the formula binds itself; a code shadowed that way is not a dependency.
		bound = {
			node.id
			for node in ast.walk(tree)
			if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
		}
		found = {
			node.id
			for node in ast.walk(tree)
			if isinstance(node, ast.Name)
			and node.id in available_codes
			and node.id not in called_names
			and node.id not in bound
		}

	# sorted so the order is the same in every process
	return sorted(found)
