# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import re

import frappe
from frappe import _
from frappe.model.document import Document


class InvalidFormulaVariable(frappe.ValidationError):
	pass


class SupplierScorecardCriteria(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		criteria_name: DF.Data
		formula: DF.SmallText
		max_score: DF.Float
		weight: DF.Percent
	# end: auto-generated types

	def validate(self):
		self.validate_variables()
		self.validate_formula()

	def validate_variables(self):
		# make sure all the variables exist
		_get_variables(self)

	def validate_formula(self):
		# evaluate the formula with 0's to make sure it is valid
		test_formula = self.formula.replace("\r", "").replace("\n", "")

		regex = r"\{(.*?)\}"

		mylist = re.finditer(regex, test_formula, re.MULTILINE | re.DOTALL)
		for _dummy1, match in enumerate(mylist):
			for _dummy2 in range(0, len(match.groups())):
				test_formula = test_formula.replace("{" + match.group(1) + "}", "1")

		try:
			frappe.safe_eval(test_formula, None, {"max": max, "min": min})
		except Exception:
			frappe.throw(_("Error evaluating the criteria formula"))


@frappe.whitelist()
def get_criteria_list():
	"""
	Get the list of criteria
	"""
	return frappe.get_list("Supplier Scorecard Criteria", fields=["name"])


def get_variables(criteria_name):
	criteria = frappe.get_doc("Supplier Scorecard Criteria", criteria_name)
	return _get_variables(criteria)


def _get_variables(criteria):
	my_variables = []
	regex = r"\{(.*?)\}"

	mylist = re.finditer(regex, criteria.formula, re.MULTILINE | re.DOTALL)
	for _dummy1, match in enumerate(mylist):
		for _dummy2 in range(0, len(match.groups())):
			param_name = match.group(1)

			variables = frappe.get_all(
				"Supplier Scorecard Variable",
				fields=["variable_label", "description", "param_name", "path"],
				filters={"param_name": param_name},
				limit=1,
			)
			if not variables:
				frappe.throw(_("Unable to find variable: {0}").format(param_name), InvalidFormulaVariable)
			my_variables.append(variables[0])

	return my_variables
