# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestQualityInspectionTemplate(ERPNextTestSuite):
	def test_duplicate_parameters(self):
		template = frappe.get_doc(
			{
				"doctype": "Quality Inspection Template",
				"item_quality_inspection_parameter": [
					{"specification": "Length"},
					{"specification": "Length"},
				],
			}
		)

		self.assertRaisesRegex(frappe.ValidationError, "must be unique", template.validate)
