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
