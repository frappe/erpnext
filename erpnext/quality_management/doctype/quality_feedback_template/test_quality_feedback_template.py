# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestQualityFeedbackTemplate(ERPNextTestSuite):
	def test_blank_and_duplicate_parameters_refused(self):
		for parameters in (["Quality", ""], ["Quality", "Quality"]):
			template = frappe.get_doc(
				doctype="Quality Feedback Template",
				template="Test Template",
				parameters=[dict(parameter=p) for p in parameters],
			)
			self.assertRaises(frappe.ValidationError, template.insert)
