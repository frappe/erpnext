# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

class TestQualityFeedback(unittest.TestCase):

	def test_quality_feedback(self):
		test_create_feedback = create_feedback()
		test_get_feedback = get_feedback()
		self.assertEquals(test_create_feedback, test_get_feedback)

def create_feedback():

	if not frappe.db.exists("User", "quality_user@test.com"):
		user = frappe.get_doc({
			"doctype": "User",
			"email": "quality_user@test.com",
			"first_name": "Quality User"
		}).insert(ignore_permissions=True)

	feedback = frappe.get_doc({
		"doctype": "Quality Feedback",
		"user": "quality_user@test.com",
		"rating": "3",
		"date": frappe.utils.today()
	})
	feedback_exist = frappe.db.get_value("Quality Feedback", {"user": "quality_user@test.com"}, "name")
	if feedback_exist:
		feedback.insert(ignore_permissions=True)
		return feedback.name
	else:
		return feedback_exist

def get_feedback():
	return frappe.db.get_value("Quality Feedback", {"user": "quality_user@test.com"}, "name")
