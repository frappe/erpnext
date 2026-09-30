# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import frappe

from erpnext.buying.doctype.supplier_scorecard_variable.supplier_scorecard_variable import (
	VariablePathNotFound,
)
from erpnext.tests.utils import ERPNextTestSuite

CUSTOM_APP = "custom_scorecard_app"
CUSTOM_VARIABLES_SOURCE = """
def get_value(scorecard):
	return 7


class Metrics:
	@staticmethod
	def get_value(scorecard):
		return 7
"""


class TestSupplierScorecardPeriod(ERPNextTestSuite):
	def test_criteria_score_is_clamped_to_bounds(self):
		period = make_period(
			criteria=[
				{"criteria_name": "Over", "formula": "200", "max_score": 100, "weight": 50},
				{"criteria_name": "Negative", "formula": "-50", "max_score": 100, "weight": 50},
			]
		)
		period.calculate_criteria()

		self.assertEqual(period.criteria[0].score, 100)  # capped at max_score
		self.assertEqual(period.criteria[1].score, 0)  # floored at zero

	def test_invalid_criteria_formula_raises(self):
		period = make_period(
			criteria=[{"criteria_name": "Bad", "formula": "{missing} +", "max_score": 100, "weight": 100}]
		)
		self.assertRaises(frappe.ValidationError, period.calculate_criteria)

	def test_eval_statement_substitutes_variable_values(self):
		period = make_period(
			variables=[
				{"variable_label": "A", "param_name": "a", "path": "get_total_workdays", "value": 5},
				{"variable_label": "B", "param_name": "b", "path": "get_total_workdays", "value": 0},
			]
		)
		# get_eval_statement checks `if var.value:` (truthiness), so a falsy value -
		# whether 0 or None - is substituted as "0.0", while a real value is formatted
		self.assertEqual(period.get_eval_statement("{a} + {b}"), "5.00 + 0.0")

	def test_period_score_is_weighted_sum_of_criteria(self):
		period = make_period(
			criteria=[
				{"criteria_name": "C1", "formula": "80", "max_score": 100, "weight": 25},
				{"criteria_name": "C2", "formula": "40", "max_score": 100, "weight": 75},
			]
		)
		period.calculate_criteria()
		period.calculate_score()

		# 80 * 0.25 + 40 * 0.75 = 50
		self.assertEqual(period.total_score, 50)

	def test_criteria_weights_must_total_100(self):
		period = make_period(
			criteria=[{"criteria_name": "C1", "formula": "100", "max_score": 100, "weight": 60}]
		)
		self.assertRaises(frappe.ValidationError, period.validate_criteria_weights)

	def test_custom_variable_path_in_unimported_module(self):
		for attribute in ("get_value", "Metrics.get_value"):
			with self.subTest(attribute=attribute):
				path = f"{CUSTOM_APP}.variables.{attribute}"
				variable = make_variable(path)
				period = make_period(
					variables=[{"variable_label": "Custom", "param_name": "custom", "path": path}]
				)

				with unimported_custom_app():
					variable.validate_path_exists()

				with unimported_custom_app():
					period.calculate_variables()

				self.assertEqual(period.variables[0].value, 7)

	def test_variable_path_outside_installed_apps_is_rejected(self):
		period = make_period(variables=[{"variable_label": "OS", "param_name": "os", "path": "os.getcwd"}])
		self.assertRaises(frappe.AppNotInstalledError, period.calculate_variables)

	def test_missing_variable_path_is_rejected(self):
		for path in ("erpnext.no_such_module.get_value", f"{CUSTOM_APP}.variables.missing"):
			with self.subTest(path=path):
				variable = make_variable(path)
				with unimported_custom_app():
					self.assertRaises(VariablePathNotFound, variable.validate_path_exists)

	def test_variable_module_import_error_is_not_hidden(self):
		variable = make_variable(f"{CUSTOM_APP}.broken.get_value")
		with unimported_custom_app():
			self.assertRaises(ModuleNotFoundError, variable.validate_path_exists)


@contextmanager
def unimported_custom_app():
	with tempfile.TemporaryDirectory() as directory:
		package = Path(directory, CUSTOM_APP)
		package.mkdir()
		(package / "__init__.py").touch()
		(package / "variables.py").write_text(CUSTOM_VARIABLES_SOURCE)
		(package / "broken.py").write_text("import scorecard_missing_dependency\n")
		installed_apps = [*frappe.get_installed_apps(), CUSTOM_APP]
		with (
			patch.object(sys, "path", [directory, *sys.path]),
			patch.dict(sys.modules),
			patch.object(frappe, "get_installed_apps", return_value=installed_apps),
		):
			yield


def make_variable(path):
	return frappe.get_doc({"doctype": "Supplier Scorecard Variable", "path": path})


def make_period(variables=None, criteria=None):
	period = frappe.new_doc("Supplier Scorecard Period")
	for variable in variables or []:
		period.append("variables", variable)
	for criterion in criteria or []:
		period.append("criteria", criterion)
	return period
