# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.stock.doctype.quality_inspection.test_quality_inspection import (
	create_quality_inspection_parameter,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestQualityInspectionTemplate(ERPNextTestSuite):
	def test_duplicate_parameters_identify_row_and_parameter(self):
		parameter = "_Test QIT Colour"
		create_quality_inspection_parameter(parameter)
		template = frappe.new_doc("Quality Inspection Template")
		template.quality_inspection_template_name = frappe.generate_hash(length=10)
		template.append("item_quality_inspection_parameter", {"specification": parameter, "value": "Red"})
		template.append("item_quality_inspection_parameter", {"specification": parameter, "value": "Blue"})

		with self.assertRaisesRegex(
			frappe.ValidationError, "Row #2: Parameter .*_Test QIT Colour.* is added more than once"
		):
			template.insert()
