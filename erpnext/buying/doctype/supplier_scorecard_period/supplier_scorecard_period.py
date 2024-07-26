# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _, throw
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc

import erpnext.buying.doctype.supplier_scorecard_variable.supplier_scorecard_variable as variable_functions
from erpnext.buying.doctype.supplier_scorecard_criteria.supplier_scorecard_criteria import (
	get_variables,
)


class SupplierScorecardPeriod(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.buying.doctype.supplier_scorecard_scoring_criteria.supplier_scorecard_scoring_criteria import (
			SupplierScorecardScoringCriteria,
		)
		from erpnext.buying.doctype.supplier_scorecard_scoring_variable.supplier_scorecard_scoring_variable import (
			SupplierScorecardScoringVariable,
		)

		amended_from: DF.Link | None
		criteria: DF.Table[SupplierScorecardScoringCriteria]
		end_date: DF.Date
		naming_series: DF.Literal["PU-SSP-.YYYY.-"]
		scorecard: DF.Link
		start_date: DF.Date
		supplier: DF.Link
		total_score: DF.Percent
		variables: DF.Table[SupplierScorecardScoringVariable]
	# end: auto-generated types

	def validate(self):
		self.validate_criteria_weights()
		self.calculate_variables()
		self.calculate_criteria()
		self.calculate_score()

	def validate_criteria_weights(self):
		weight = 0
		for c in self.criteria:
			weight += c.weight

		if weight != 100:
			throw(_("Criteria weights must add up to 100%"))

	def calculate_variables(self):
		for var in self.variables:
			if "." in var.path:
				method_to_call = import_string_path(var.path)
				var.value = method_to_call(self)
			else:
				method_to_call = getattr(variable_functions, var.path)
				var.value = method_to_call(self)

	def calculate_criteria(self):
		for crit in self.criteria:
			try:
				crit.score = min(
					crit.max_score,
					max(
						0,
						frappe.safe_eval(
							self.get_eval_statement(crit.formula), None, {"max": max, "min": min}
						),
					),
				)
			except Exception:
				frappe.throw(
					_(
						"Could not solve criteria score function for {0}. Make sure the formula is valid."
					).format(crit.criteria_name),
					frappe.ValidationError,
				)
				crit.score = 0

	def calculate_score(self):
		myscore = 0
		for crit in self.criteria:
			myscore += crit.score * crit.weight / 100.0
		self.total_score = myscore

	def calculate_weighted_score(self, weighing_function):
		try:
			weighed_score = frappe.safe_eval(
				self.get_eval_statement(weighing_function), None, {"max": max, "min": min}
			)
		except Exception:
			frappe.throw(
				_("Could not solve weighted score function. Make sure the formula is valid."),
				frappe.ValidationError,
			)
			weighed_score = 0
		return weighed_score

	def get_eval_statement(self, formula):
		my_eval_statement = formula.replace("\r", "").replace("\n", "")

		for var in self.variables:
			if var.value:
				if var.param_name in my_eval_statement:
					my_eval_statement = my_eval_statement.replace(
						"{" + var.param_name + "}", f"{var.value:.2f}"
					)
			else:
				if var.param_name in my_eval_statement:
					my_eval_statement = my_eval_statement.replace("{" + var.param_name + "}", "0.0")

		return my_eval_statement


def import_string_path(path):
	components = path.split(".")
	mod = __import__(components[0])
	for comp in components[1:]:
		mod = getattr(mod, comp)
	return mod


def make_supplier_scorecard(source_name, target_doc=None):
	def update_criteria_fields(obj, target, source_parent):
		target.max_score, target.formula = frappe.db.get_value(
			"Supplier Scorecard Criteria", obj.criteria_name, ["max_score", "formula"]
		)

	def post_process(source, target):
		variables = []
		for cr in target.criteria:
			for var in get_variables(cr.criteria_name):
				if var not in variables:
					variables.append(var)

		target.extend("variables", variables)

	doc = get_mapped_doc(
		"Supplier Scorecard",
		source_name,
		{
			"Supplier Scorecard": {"doctype": "Supplier Scorecard Period"},
			"Supplier Scorecard Scoring Criteria": {
				"doctype": "Supplier Scorecard Scoring Criteria",
				"postprocess": update_criteria_fields,
			},
		},
		target_doc,
		post_process,
		ignore_permissions=True,
	)

	return doc
