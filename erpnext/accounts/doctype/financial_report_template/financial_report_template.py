# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json
import re

import frappe
from frappe import _
from frappe.model.document import Document

FORMULA_REGEX = r"\b[A-Za-z][A-Za-z0-9_-]*\b"


class FinancialReportTemplate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.financial_report_row.financial_report_row import FinancialReportRow

		disabled: DF.Check
		is_standard: DF.Check
		module: DF.Link | None
		report_type: DF.Literal["", "Profit and Loss Statement", "Balance Sheet"]
		rows: DF.Table[FinancialReportRow]
		template_name: DF.Data
	# end: auto-generated types

	# Class constants for validation
	from typing import ClassVar

	def validate(self):
		self.validate_reference_codes()
		self.validate_row_content()
		self.validate_references()

	# === Reference Code Validation ===
	def validate_reference_codes(self):
		self._check_unique_reference_codes()
		self._check_reference_code_format()

	def _check_unique_reference_codes(self):
		used_codes = set()

		for row in self.rows:
			if not row.reference_code:
				continue

			reference_code = row.reference_code.strip()
			if reference_code in used_codes:
				frappe.throw(
					_("Duplicate Reference Code {0} found in row {1}").format(reference_code, row.idx)
				)

			used_codes.add(reference_code)

	def _check_reference_code_format(self):
		"""Validate reference code format - alphanumeric, underscore, hyphen only."""
		valid_pattern = re.compile(FORMULA_REGEX)

		for row in self.rows:
			if not row.reference_code:
				continue

			reference_code = row.reference_code.strip()
			if not valid_pattern.match(reference_code):
				frappe.throw(
					_(
						"Reference Code {0} in row {1} is invalid. Must start with a letter and contain only letters, numbers, underscores, and hyphens."
					).format(reference_code, row.idx)
				)

	# === Row Content Validation ===
	def validate_row_content(self):
		self._validate_required_fields()
		self._validate_formulas()

	def _validate_required_fields(self):
		for row in self.rows:
			if row.data_source == "Account Data" and not row.balance_type:
				frappe.throw(_("Balance Type is required for Account Data row {0}").format(row.idx))

			if (
				row.data_source in ["Account Data", "Calculated Amount", "Custom API"]
				and not row.calculation_formula
			):
				frappe.throw(_("Calculation Formula is required for row {0}").format(row.idx))

	def _validate_formulas(self):
		if not self.rows:
			return

		rows_by_code = {row.reference_code: row for row in self.rows if row.reference_code}
		dependencies = {}

		for row in self.rows:
			if not row.calculation_formula:
				continue

			if row.data_source == "Calculated Amount":
				self._check_balanced_parentheses(row)
				self._check_self_reference(row, rows_by_code)

				deps = self._extract_reference_codes_from_formula(
					row.calculation_formula, rows_by_code.keys()
				)
				dependencies[row.reference_code] = deps

			elif row.data_source == "Account Data":
				try:
					filter_config = json.loads(row.calculation_formula)
					self._validate_account_filter_structure(filter_config, row)
				except json.JSONDecodeError:
					frappe.throw(_("Row {0}: Invalid JSON format in account filter").format(row.idx))

			elif row.data_source == "Custom API":
				if "." not in row.calculation_formula:
					frappe.throw(
						_("Row {0}: Custom API path should be in format: app.module.method").format(row.idx)
					)

		if dependencies:
			from erpnext.accounts.doctype.financial_report_template.financial_report_engine import (
				DependencyResolver,
			)

			DependencyResolver.check_circular_references(dependencies)

	# === Formula Validation Helpers ===
	def _check_balanced_parentheses(self, row):
		formula = row.calculation_formula
		if formula.count("(") != formula.count(")"):
			frappe.throw(_("Row {0}: Formula has unbalanced parentheses").format(row.idx))

	def _check_self_reference(self, row, rows_by_code):
		if not row.reference_code:
			return

		referenced_codes = self._extract_reference_codes_from_formula(
			row.calculation_formula, rows_by_code.keys()
		)
		if row.reference_code in referenced_codes:
			frappe.throw(_("Row {0} references itself in its formula").format(row.idx))

	def _extract_reference_codes_from_formula(self, formula, available_codes):
		found_codes = []
		for code in available_codes:
			# Match complete words only to avoid partial matches
			pattern = r"\b" + re.escape(code) + r"\b"
			if re.search(pattern, formula):
				found_codes.append(code)

		return found_codes

	def validate_references(self):
		"""Validate that all reference codes in formulas exist and check for circular dependencies"""
		# This is a basic validation - comprehensive validation happens in DependencyResolver
		all_formulas = {}

		# Check row level formulas
		for row in self.rows or []:
			if row.data_source == "Calculated Amount" and row.calculation_formula:
				if row.reference_code:
					all_formulas[row.reference_code] = row.calculation_formula

		# Only proceed if we have formulas to validate
		if not all_formulas:
			return

		# Build example context with all reference codes set to sample values
		example_context = {}
		for row in self.rows:
			if row.reference_code:
				example_context[row.reference_code] = 1000.0  # Sample value

		# Validate each formula using the FormulaCalculator's validation method
		from erpnext.accounts.doctype.financial_report_template.financial_report_engine import (
			FormulaCalculator,
		)

		for ref_code, formula in all_formulas.items():
			error_message = FormulaCalculator.validate_formula_with_context(formula, example_context)
			if error_message:
				frappe.throw(_("Invalid formula in '{0}': {1}").format(ref_code, error_message))

	# === Account Filter Validation ===
	def _validate_account_filter_structure(self, filter_config, row):
		"""
		Examples:
		- Simple: ["account_type", "=", "Asset"]
		- Complex: {"and": [["account_type", "=", "Asset"], ["is_group", "=", 0]]}
		"""

		if isinstance(filter_config, list) and len(filter_config) == 3:
			self._validate_simple_filter_condition(filter_config, row)
		elif isinstance(filter_config, dict):
			self._validate_logical_filter_condition(filter_config, row)
		else:
			frappe.throw(
				_("Row {0}: Account filter must be a simple condition or logical condition").format(row.idx)
			)

	def _validate_simple_filter_condition(self, condition, row):
		field, operator, __ = condition
		valid_operators = ["=", "==", "!=", "<>", "in", "not in", "like", "not like", "is"]

		if not isinstance(field, str) or not isinstance(operator, str):
			frappe.throw(
				_('Row {0}: Filter condition must be ["field", "operator", "value"]').format(row.idx)
			)

		if operator not in valid_operators:
			frappe.throw(
				_("Row {0}: Invalid operator '{1}'. Valid operators: {2}").format(
					row.idx, operator, ", ".join(valid_operators)
				)
			)

	def _validate_logical_filter_condition(self, condition_dict, row):
		logical_operators = list(condition_dict.keys())
		if len(logical_operators) != 1 or logical_operators[0] not in ["and", "or"]:
			frappe.throw(_("Row {0}: Logical conditions must use 'and' or 'or' operators").format(row.idx))

		sub_conditions = condition_dict[logical_operators[0]]
		if not isinstance(sub_conditions, list) or len(sub_conditions) < 2:
			frappe.throw(_("Row {0}: Logical conditions must have at least 2 sub-conditions").format(row.idx))

		for sub_condition in sub_conditions:
			self._validate_account_filter_structure(sub_condition, row)

	# === Template Management ===
	def on_update(self):
		if self.is_standard:
			self._prevent_standard_template_modification()

		self._export_template()

	def _prevent_standard_template_modification(self):
		if not (self._doc_before_save and self._doc_before_save.is_standard):
			return

		protected_fields = ["template_name", "report_type", "module"]
		for field in protected_fields:
			if self.get(field) != self._doc_before_save.get(field):
				field_label = _(field.replace("_", " ").title())
				frappe.throw(_("Cannot modify {0} in standard template").format(field_label))

	def _export_template(self):
		from frappe.modules.utils import export_module_json

		return export_module_json(self, self.is_standard == 1, self.module)
