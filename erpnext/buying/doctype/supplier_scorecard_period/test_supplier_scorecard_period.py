# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


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


def make_period(variables=None, criteria=None):
	period = frappe.new_doc("Supplier Scorecard Period")
	for variable in variables or []:
		period.append("variables", variable)
	for criterion in criteria or []:
		period.append("criteria", criterion)
	return period
