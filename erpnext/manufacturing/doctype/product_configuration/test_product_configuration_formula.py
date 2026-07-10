import frappe
from frappe.tests import IntegrationTestCase

from erpnext.manufacturing.doctype.product_configuration.formula import build_context, evaluate


class TestProductConfigurationFormula(IntegrationTestCase):
	def test_functions_and_arithmetic(self):
		context = build_context({"width": 2.0, "height": 3.0})
		self.assertEqual(evaluate("width * height", context)["value"], 6.0)
		self.assertEqual(evaluate("CEILING(width * height / 4)", context)["value"], 2)
		self.assertEqual(evaluate("IF(width > 1, 10, 5)", context)["value"], 10)
		self.assertEqual(evaluate("MAX(width, height)", context)["value"], 3.0)
		self.assertEqual(evaluate("ROUNDUP(2.1, 0)", context)["value"], 3)

	def test_derived_variables_chain(self):
		variables = [
			{"variable_name": "area", "formula": "width * height"},
			{"variable_name": "panels", "formula": "CEILING(area / 2)"},
		]
		context = build_context({"width": 2.0, "height": 3.0}, variables)
		self.assertEqual(context["area"], 6.0)
		self.assertEqual(context["panels"], 3)

	def test_unknown_variable_in_derived_formula_raises(self):
		variables = [{"variable_name": "area", "formula": "width * heigth"}]
		with self.assertRaises(frappe.ValidationError) as caught:
			build_context({"width": 2.0}, variables)
		self.assertIn("area", str(caught.exception))
		self.assertIn("heigth", str(caught.exception))

	def test_bad_formula_returns_error(self):
		result = evaluate("width *", {"width": 1})
		self.assertFalse(result["ok"])
		self.assertIn("error", result)

	def test_injection_is_blocked(self):
		self.assertFalse(evaluate("__import__('os').system('echo hi')", {})["ok"])
		self.assertFalse(evaluate("(lambda: 1)()", {})["ok"])
