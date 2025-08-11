# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _
from frappe.model.document import Document


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

	def validate(self):
		self.validate_duplicate_reference_codes()
		self.validate_formula_syntax()
		self.validate_report_structure()
		self.validate_reference_code_format()

	def validate_duplicate_reference_codes(self):
		seen_codes = set()

		for row in self.rows:
			if not row.reference_code:
				continue

			code = row.reference_code.strip()

			if code in seen_codes:
				frappe.throw(_("Duplicate Reference Code {0} found in row {1}").format(code, row.idx))

			seen_codes.add(code)

	def validate_formula_syntax(self):
		if not self.rows:
			return

		row_map = {row.reference_code: row for row in self.rows if row.reference_code}

		for row in self.rows:
			if row.data_type == "Calculated Amount" and row.calculation_formula:
				# self-reference
				referenced_codes = self.extract_codes_from_formula(row.calculation_formula, row_map.keys())
				if row.reference_code and row.reference_code in referenced_codes:
					frappe.throw(_("Row {0} references itself in its formula").format(row.idx))

				# circular references
				visited = set()
				if row.reference_code:
					self.check_circular_reference(row.reference_code, referenced_codes, row_map, visited)

	def validate_report_structure(self):
		for row in self.rows:
			if row.data_type == "Account Data" and not row.balance_type:
				frappe.throw(_("Data Source is required for Account Data row {0}").format(row.idx))

			if row.data_type in ["Calculated Amount", "Account Data"] and not row.calculation_formula:
				frappe.throw(_("Calculation Formula is required for row {0}").format(row.idx))

	def validate_reference_code_format(self):
		# Allow alphanumeric characters, underscores, and hyphens
		# Avoid characters that could interfere with formula parsing like +, -, *, /, (, ), etc.
		pattern = re.compile(r"^[A-Za-z0-9_-]+$")

		for row in self.rows:
			if row.reference_code:
				code = row.reference_code.strip()
				if not pattern.match(code):
					frappe.throw(
						_(
							"Reference Code {0} in row {1} contains invalid characters. Use only letters, numbers, underscores, and hyphens."
						).format(code, row.idx)
					)

				# Ensure it doesn't start with a number (to avoid confusion with numeric literals)
				if code and code[0].isdigit():
					frappe.throw(
						_("Reference Code {0} in row {1} cannot start with a number.").format(code, row.idx)
					)

	def extract_codes_from_formula(self, formula, valid_codes):
		found_codes = []
		for code in valid_codes:
			# match complete codes
			pattern = r"\b" + re.escape(code) + r"\b"
			if re.search(pattern, formula):
				found_codes.append(code)

		return found_codes

	def check_circular_reference(self, current_code, codes_to_check, row_map, visited):
		visited.add(current_code)

		for code in codes_to_check:
			if code in visited:
				frappe.throw(
					_("Circular reference detected in formulas between {0} and {1}").format(
						current_code, code
					)
				)

			row = row_map.get(code)
			if row and row.data_type == "Calculated Amount" and row.calculation_formula:
				next_check = self.extract_codes_from_formula(row.calculation_formula, row_map.keys())

				# recursively check
				self.check_circular_reference(code, next_check, row_map, visited.copy())

	def on_update(self):
		if self.is_standard:
			# Check if system fields were modified for standard templates
			if self._doc_before_save and self._doc_before_save.is_standard:
				# Compare critical fields
				for field in ["template_name", "report_type", "module"]:
					if self.get(field) != self._doc_before_save.get(field):
						frappe.throw(
							_("Cannot modify {0} in standard template").format(
								_(field.replace("_", " ").title())
							)
						)

		self.export_doc()

	def export_doc(self):
		from frappe.modules.utils import export_module_json

		return export_module_json(self, self.is_standard == 1, self.module)
