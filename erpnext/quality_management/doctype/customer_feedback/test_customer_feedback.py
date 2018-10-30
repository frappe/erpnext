# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

class TestCustomerFeedback(unittest.TestCase):
	
	def test_customer_feedback(self):
		test_create_feedback = create_feedback()
		test_get_feedback = get_feedback()
		self.assertEquals(test_create_feedback.name, test_get_feedback.name)

def create_feedback():
	feedback = frappe.get_doc({
		"doctype": "Customer Feedback",
		"date": ""+ frappe.utils.nowdate() +""
	})
	feedback_exist = frappe.get_list("Customer Feedback", filters={"date": ""+ feedback.date +""})
	if len(feedback_exist) == 0:
		feedback.insert()
		return feedback
	else:
		return feedback_exist[0]

def get_feedback():
	feedback = frappe.get_list("Customer Feedback")
	return feedback[0]