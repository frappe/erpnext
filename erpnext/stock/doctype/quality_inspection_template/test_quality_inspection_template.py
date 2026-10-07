# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.quality_inspection.test_quality_inspection import (
	create_quality_inspection_parameter,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestQualityInspectionTemplate(ERPNextTestSuite):
	def make_template(self, *rows):
		template = frappe.new_doc("Quality Inspection Template")
		template.quality_inspection_template_name = frappe.generate_hash(length=10)
		for row in rows:
			create_quality_inspection_parameter(row["specification"])
			template.append("item_quality_inspection_parameter", row)

		return template

	def test_formula_based_row_requires_formula(self):
		template = self.make_template({"specification": "_Test QIT Moisture", "formula_based_criteria": 1})
		self.assertRaises(frappe.ValidationError, template.insert)

	def test_rows_that_can_never_pass_are_rejected(self):
		invalid_rows = (
			[{"specification": "_Test QIT Length", "numeric": 1, "min_value": 10, "max_value": 5}],
			[{"specification": "_Test QIT Length", "numeric": 1, "min_value": 5}],
			[{"specification": "_Test QIT Colour", "numeric": 0}],
			[
				{"specification": "_Test QIT Colour", "numeric": 0, "value": "Red"},
				{"specification": "_Test QIT Colour", "numeric": 0, "value": "Blue"},
			],
		)

		for rows in invalid_rows:
			with self.subTest(rows=rows):
				self.assertRaises(frappe.ValidationError, self.make_template(*rows).insert)

	def test_valid_rows_are_saved(self):
		template = self.make_template(
			{"specification": "_Test QIT Length", "numeric": 1, "min_value": 5, "max_value": 10},
			{"specification": "_Test QIT Colour", "numeric": 0, "value": "Red"},
		)
		template.insert()
		self.assertTrue(template.name)
