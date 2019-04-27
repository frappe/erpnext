# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

class TestQualityFeedbackTemplate(unittest.TestCase):

	def test_quality_feedback_template(self):
		test_create_template = create_template()
		test_get_template = get_template()
		self.assertEquals(test_get_template, test_create_template)

def create_template():
	template = frappe.get_doc({
		"doctype": "Quality Feedback Template",
		"template_name": "_Test Quality Feedback Template",
		"feedback_parameter": [
			{
				"parameter": "_Test Quality Feedback Template Parameter",
			}
		]
	})
	template_exist = frappe.db.get_value("Quality Feedback Template", "TMPL-_Test Quality Feedback Template")
	if not template_exist:
		template.insert()
		return template.name
	else:
		return template_exist

def get_template():
	return frappe.db.get_value("Quality Feedback Template", "TMPL-_Test Quality Feedback Template")