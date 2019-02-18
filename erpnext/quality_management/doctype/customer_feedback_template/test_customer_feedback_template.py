# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

class TestCustomerFeedbackTemplate(unittest.TestCase):
	def test_customer_feedback_template(self):
		test_create_template = create_template()
		test_get_template = get_template()
		self.assertEquals(test_get_template.name, test_create_template.name)

def create_template():
	template = frappe.get_doc({
		"doctype": "Customer Feedback Template",
		"template": "_Test Customer Feedback Template",
		"scope": "Company",
		"feedback_parameter": [
			{
				"parameter": "_Test Customer Feedback Template Parameter",
			}
		]
	})
	template_exist = frappe.get_list("Customer Feedback Template", filters={"template": ""+ template.template +""}, fields=["name"], limit=1)
	if len(template_exist) == 0:
		template.insert()
		return template
	else:
		return template_exist[0]

def get_template():
	template = frappe.get_list("Customer Feedback Template", filters={"template": "_Test Customer Feedback Template"}, limit=1)
	return template[0]