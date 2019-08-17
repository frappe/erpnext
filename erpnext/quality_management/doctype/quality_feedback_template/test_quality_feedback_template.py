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

		self.assertEqual(test_create_template, test_get_template)

def create_template():
	template = frappe.get_doc({
		"doctype": "Quality Feedback Template",
		"template": "_Test Feedback Template",
		"parameters": [
			{
				"parameter": "Test Parameter"
			}
		]
	})

	template_exists = frappe.db.exists("Quality Feedback Template", {"template": "_Test Feedback Template"})

	if not template_exists:
		template.insert()
		return template.name
	else:
		return template_exists

def get_template():
	return frappe.db.exists("Quality Feedback Template", {"template": "_Test Feedback Template"})