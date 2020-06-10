# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.quality_management.doctype.quality_feedback_template.test_quality_feedback_template import create_template

class TestQualityFeedback(unittest.TestCase):

	def test_quality_feedback(self):
		create_template()
		test_create_feedback = create_feedback()
		test_get_feedback = get_feedback()

		self.assertEqual(test_create_feedback, test_get_feedback)

def create_feedback():
	create_customer()

	feedabck = frappe.get_doc({
		"doctype": "Quality Feedback",
		"template": "TMPL-_Test Feedback Template",
		"document_type": "Customer",
		"document_name": "Quality Feedback Customer",
		"date": frappe.utils.nowdate(),
		"parameters": [
			{
				"parameter": "Test Parameter",
				"rating": 3,
				"feedback": "Test Feedback"
			}
		]
	})

	feedback_exists = frappe.db.exists("Quality Feedback", {"template": "TMPL-_Test Feedback Template"})

	if not feedback_exists:
		feedabck.insert()
		return feedabck.name
	else:
		return feedback_exists

def get_feedback():
	return frappe.db.exists("Quality Feedback", {"template": "TMPL-_Test Feedback Template"})

def create_customer():
	if not frappe.db.exists("Customer", {"customer_name": "Quality Feedback Customer"}):
		customer = frappe.get_doc({
				"doctype": "Customer",
				"customer_name": "Quality Feedback Customer"
			}).insert(ignore_permissions=True)