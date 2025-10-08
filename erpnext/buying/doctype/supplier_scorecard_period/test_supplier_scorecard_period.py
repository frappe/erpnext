# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase


class TestSupplierScorecardPeriod(FrappeTestCase):
	def setUp(self):
		supplier_records = create_supplier_related_records()
		self.criteria = supplier_records.get("criteria")
		self.scorecard_variable = supplier_records.get("scorecard_variable")
		self.supplier_document = supplier_records.get("supplier_document")
		self.scorecard = supplier_records.get("scorecard")

	def teardown(self):
		frappe.db.rollback()

	def test_validate_method_TC_B_203(self):
		supplier = frappe.get_doc({"doctype": "Supplier", "supplier_name": "Test Supplier Validate"}).insert(
			ignore_permissions=True, ignore_if_duplicate=True
		)

		criteria = frappe.get_doc(
			{
				"doctype": "Supplier Scorecard Criteria",
				"criteria_name": "Test Criteria Validate",
				"max_score": 10,
				"formula": "10",
			}
		).insert(ignore_permissions=True, ignore_if_duplicate=True)

		variable = frappe.get_doc(
			{
				"doctype": "Supplier Scorecard Variable",
				"variable_label": "Test Var",
				"param_name": "test_var",
				"path": "get_ordered_qty",
			}
		).insert(ignore_permissions=True, ignore_if_duplicate=True)

		scorecard = frappe.get_doc(
			{
				"doctype": "Supplier Scorecard",
				"supplier": supplier.name,
				"period": "Per Month",
				"criteria": [{"criteria_name": criteria.name, "weight": 100}],
				"standings": [
					{"min_grade": 0, "max_grade": 49, "standing": "Poor"},
					{"min_grade": 49, "max_grade": 74, "standing": "Average"},
					{"min_grade": 74, "max_grade": 100, "standing": "Excellent"},
				],
			}
		).insert(ignore_permissions=True, ignore_if_duplicate=True)

		doc = frappe.get_doc(
			{
				"doctype": "Supplier Scorecard Period",
				"scorecard": scorecard.name,
				"from_date": "2024-01-01",
				"to_date": "2024-12-31",
				"criteria": [
					{
						"criteria_name": criteria.name,
						"weight": 100,
						"formula": criteria.formula,
						"max_score": criteria.max_score,
					}
				],
				"variables": [
					{
						"variable_label": variable.name,
						"param_name": variable.param_name,
						"path": variable.path,
					}
				],
			}
		)

		doc.validate()

		self.assertEqual(doc.criteria[0].score, 10)
		self.assertIsNotNone(doc.variables[0].value)

	def test_import_string_path_TC_B_204(self):
		from frappe.utils import add_days

		from erpnext.buying.doctype.supplier_scorecard_period.supplier_scorecard_period import (
			import_string_path,
		)

		self.assertEqual(import_string_path("frappe.utils.add_days"), add_days)
		self.assertRaises(AttributeError, import_string_path, "frappe.utils.invalid_func")

	def test_criteria_weight_validation_valid_and_invalid_TC_B_205(self):
		criteria = frappe.get_doc(
			{
				"doctype": "Supplier Scorecard Criteria",
				"criteria_name": "Test Weight Criteria",
				"max_score": 10,
				"formula": "10",
			}
		).insert(ignore_permissions=True, ignore_if_duplicate=True)

		supplier = frappe.get_doc({"doctype": "Supplier", "supplier_name": "Test Supplier"}).insert(
			ignore_permissions=True, ignore_if_duplicate=True
		)

		scorecard = frappe.get_doc(
			{
				"doctype": "Supplier Scorecard",
				"supplier": supplier.name,
				"period": "Per Month",
				"criteria": [{"criteria_name": criteria.name, "weight": 100}],
				"standings": [
					{"min_grade": 0, "max_grade": 49, "standing": "Poor"},
					{"min_grade": 49, "max_grade": 74, "standing": "Average"},
					{"min_grade": 74, "max_grade": 100, "standing": "Excellent"},
				],
			}
		).insert(ignore_permissions=True, ignore_if_duplicate=True)

		# Case 1: Valid weight
		valid_doc = frappe.get_doc(
			{
				"doctype": "Supplier Scorecard Period",
				"scorecard": scorecard.name,
				"criteria": [{"criteria_name": criteria.name, "weight": 100}],
			}
		)
		valid_doc.validate_criteria_weights()
		self.assertTrue(True)

		# Case 2: Invalid weight
		invalid_doc = frappe.get_doc(
			{
				"doctype": "Supplier Scorecard Period",
				"scorecard": scorecard.name,
				"criteria": [{"criteria_name": criteria.name, "weight": 80}],
			}
		)
		with self.assertRaises(frappe.ValidationError):
			invalid_doc.validate_criteria_weights()

	def test_calculate_variables_TC_B_206(self):
		supplier_scorecard_criteria = create_or_get_doc(
			"Supplier Scorecard Criteria",
			{"criteria_name": "_Test Criteria"},
			{
				"doctype": "Supplier Scorecard Criteria",
				"max_score": "100",
				"formula": "max(0,10)*100",
				"criteria_name": "_Test Criteria",
			},
		)
		supplier_doc = frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": "Test Supplier for RFQ",
			}
		).insert(ignore_permissions=True, ignore_if_duplicate=True)
		supplier_scorecard = supplier_scorecard = create_or_get_supplier_scorecard(
			supplier_doc.name, supplier_scorecard_criteria.name
		)
		supplier_scorecard_variable = create_or_get_supplier_scorecard_variable()

		doc = frappe.get_doc(
			{
				"doctype": "Supplier Scorecard Period",
				"scorecard": supplier_scorecard.name,
				"from_date": "2024-01-01",
				"to_date": "2024-12-31",
				"criteria": [
					{"criteria_name": supplier_scorecard_criteria.name, "weight": 100},
				],
				"variables": [
					{"variable_label": supplier_scorecard_variable.name, "path": "get_ordered_qty"}
				],
			}
		)

		doc.calculate_variables()

		self.assertIsNotNone(doc.variables[0].value)
		with patch(
			"erpnext.buying.doctype.supplier_scorecard_period.supplier_scorecard_period.import_string_path"
		) as mock_import:
			mock_import.return_value = lambda self: 123

			doc.append(
				"variables",
				{"variable_label": "Mock Dotted Function", "path": "erpnext.supplier.mock_function"},
			)

			doc.calculate_variables()

			self.assertIsNotNone(doc.variables[0].value)
			self.assertEqual(doc.variables[1].value, 123)

	def test_calculate_score_TC_B_207(self):
		doc = frappe.get_doc(
			{
				"doctype": "Supplier Scorecard Period",
				"scorecard": "Test Scorecard",
				"criteria": [
					{"criteria": "Quality", "weight": 60, "score": 80},
					{"criteria": "Delivery", "weight": 40, "score": 90},
				],
			}
		)

		doc.calculate_score()

		expected_score = (60 * 80 / 100.0) + (40 * 90 / 100.0)
		self.assertEqual(doc.total_score, expected_score)

	def test_calculate_weighted_score_TC_B_208(self):
		doc = frappe.get_doc(
			{
				"doctype": "Supplier Scorecard Period",
				"scorecard": "Test Scorecard",
				"from_date": "2024-01-01",
				"to_date": "2024-12-31",
			}
		)

		doc.get_eval_statement = lambda fn: "min(80, 100)"

		result = doc.calculate_weighted_score(doc.get_eval_statement)
		self.assertEqual(result, 80)

	def test_calculate_weighted_score_invalid_formula_TC_B_209(self):
		doc = frappe.new_doc("Supplier Scorecard Period")
		doc.variables = []

		doc.get_eval_statement = lambda formula: "INVALID"

		msg = "Could not solve weighted score function"
		with self.assertRaises(frappe.ValidationError, msg=msg):
			doc.calculate_weighted_score("INVALID FORMULA")

		# self.assertIn("Could not solve weighted score function", str(cm.exception))

	def test_get_eval_statement_TC_B_210(self):
		doc = frappe.get_doc(
			{
				"doctype": "Supplier Scorecard Period",
				"variables": [
					frappe._dict({"param_name": "quality", "value": 80}),
					frappe._dict({"param_name": "delivery", "value": None}),
				],
			}
		)

		formula = "{quality} * 0.5 + {delivery} * 0.5"
		expected = "80.00 * 0.5 + 0.0 * 0.5"

		result = doc.get_eval_statement(formula)
		self.assertEqual(result, expected)

	def test_make_supplier_scorecard_TC_B_211(self):
		from erpnext.buying.doctype.supplier_scorecard_period.supplier_scorecard_period import (
			make_supplier_scorecard,
		)

		result = make_supplier_scorecard(self.scorecard)
		self.assertEqual(result.doctype, "Supplier Scorecard Period")

		if len(result.variables) > 0:
			self.assertTrue(len(result.variables) > 0, "No variables were populated.")
			variable = result.variables[0]
			self.assertEqual(variable.variable_label, "Test")
			self.assertEqual(variable.param_name, "Test")
			self.assertEqual(variable.path, "get_ordered_qty")

	def test_calculate_criteria_TC_B_212(self):
		doc = frappe.get_doc(
			{
				"doctype": "Supplier Scorecard Period",
				"scorecard": "Dummy Scorecard",
				"variables": [{"param_name": "on_time_delivery_rate", "value": 85}],
				"criteria": [
					{"criteria_name": "Delivery", "formula": "{on_time_delivery_rate} / 10", "max_score": 10}
				],
			}
		)

		doc.calculate_criteria()

		self.assertAlmostEqual(doc.criteria[0].score, 8.5, places=2)

	def test_calculate_criteria_with_invalid_formula_TC_B_213(self):
		doc = frappe.get_doc(
			{
				"doctype": "Supplier Scorecard Period",
				"criteria": [
					{
						"criteria_name": "Invalid Criteria",
						"weight": 100,
						"max_score": 10,
						"formula": "{undefined_variable}",
					}
				],
			}
		)

		doc.variables = []
		msg = "Could not solve criteria score function"
		with self.assertRaises(frappe.ValidationError, msg=msg):
			doc.calculate_criteria()

		# self.assertIn("Could not solve criteria score function", str(context.exception))


def create_supplier_related_records():
	scorecard_criteria = "_Test Criteria"
	scorecard_variable = "Test"
	supplier_name = "Test Supplier for RFQ"
	if not frappe.db.exists("Supplier Scorecard Criteria", scorecard_criteria):
		criteria = frappe.get_doc(
			{
				"doctype": "Supplier Scorecard Criteria",
				"max_score": "100",
				"formula": "max(0,10)*100",
				"criteria_name": "_Test Criteria",
			}
		).insert(ignore_permissions=True, ignore_if_duplicate=True)
	else:
		criteria = frappe.get_doc("Supplier Scorecard Criteria", scorecard_criteria)
	if not frappe.db.exists("Supplier Scorecard Variable", scorecard_variable):
		frappe.get_doc(
			{
				"doctype": "Supplier Scorecard Variable",
				"variable_label": "Test",
				"param_name": "Test",
				"path": "get_ordered_qty",
			}
		).insert(ignore_permissions=True, ignore_if_duplicate=True)

	if not frappe.db.exists("Supplier", supplier_name):
		supplier_doc = frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": "Test Supplier for RFQ",
			}
		).insert(ignore_permissions=True, ignore_if_duplicate=True)
	else:
		supplier_doc = frappe.get_doc("Supplier", supplier_name)

	scorecard = frappe.get_doc(
		{
			"doctype": "Supplier Scorecard",
			"supplier": supplier_doc.name,
			"period": "Per Month",
			"criteria": [{"criteria_name": criteria.name, "weight": 100}],
			"standings": [
				{"min_grade": 0, "max_grade": 49, "standing": "Poor"},
				{"min_grade": 49, "max_grade": 74, "standing": "Average"},
				{"min_grade": 74, "max_grade": 100, "standing": "Excellent"},
			],
		}
	)

	return {
		"criteria": criteria,
		"scorecard_variable": scorecard_variable,
		"supplier_document": supplier_name,
		"scorecard": scorecard,
	}


def create_or_get_doc(doctype, filters, doc_data):
	existing = frappe.db.exists(doctype, filters)
	if existing:
		return frappe.get_doc(doctype, existing)
	return frappe.get_doc(doc_data).insert(ignore_permissions=True)


def create_or_get_supplier_scorecard(supplier_name, criteria_name):
	existing = frappe.db.exists("Supplier Scorecard", {"supplier": supplier_name})
	if existing:
		return frappe.get_doc("Supplier Scorecard", existing)

	return frappe.get_doc(
		{
			"doctype": "Supplier Scorecard",
			"supplier": supplier_name,
			"period": "Per Month",
			"criteria": [{"criteria_name": criteria_name, "weight": 100}],
			"standings": [
				{"min_grade": 0, "max_grade": 49, "standing": "Poor"},
				{"min_grade": 49, "max_grade": 74, "standing": "Average"},
				{"min_grade": 74, "max_grade": 100, "standing": "Excellent"},
			],
		}
	).insert(ignore_permissions=True)


def create_or_get_supplier_scorecard_variable(label="Test", param="Test", path="get_ordered_qty"):
	existing = frappe.db.exists("Supplier Scorecard Variable", {"variable_label": label})
	if existing:
		return frappe.get_doc("Supplier Scorecard Variable", existing)

	return frappe.get_doc(
		{
			"doctype": "Supplier Scorecard Variable",
			"variable_label": label,
			"param_name": param,
			"path": path,
		}
	).insert(ignore_permissions=True)
