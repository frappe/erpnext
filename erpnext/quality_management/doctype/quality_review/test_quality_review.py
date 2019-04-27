# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.quality_management.doctype.quality_procedure.test_quality_procedure import create_procedure
from erpnext.quality_management.doctype.quality_goal.test_quality_goal import create_unit
from erpnext.quality_management.doctype.quality_goal.test_quality_goal import create_goal

class TestQualityReview(unittest.TestCase):

	def test_quality_review(self):
		create_procedure()
		create_unit()
		create_goal()
		test_create_review = create_review()
		test_get_review = get_review()
		self.assertEquals(test_create_review, test_get_review)

def create_review():
	review = frappe.get_doc({
		"doctype": "Quality Review",
		"reference_doctype": "Quality Goal",
		"reference_name": "GOAL-_Test Quality Goal",
		"date": frappe.utils.today(),
		"review": "Test Review"
	})
	review_exist = frappe.db.get_value("Quality Review", {"reference_name": "GOAL-_Test Quality Goal"}, "name")
	if not review_exist:
		review.insert(ignore_permissions=True)
		return review.name
	else:
		return review_exist

def get_review():
	return frappe.db.get_value("Quality Review", {"reference_name": "GOAL-_Test Quality Goal"}, "name")