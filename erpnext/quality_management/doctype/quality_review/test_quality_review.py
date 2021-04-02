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
		"goal": "GOAL-_Test Quality Goal",
		"procedure": "PRC-_Test Quality Procedure",
		"date": frappe.utils.nowdate(),
		"reviews": [
			{
				"objective": "_Test Quality Objective",
				"target": "100",
				"uom": "_Test UOM",
				"review": "Test Review"
			}
		]
	})
	review_exist = frappe.db.exists("Quality Review", {"goal": "GOAL-_Test Quality Goal"})
	if not review_exist:
		review.insert(ignore_permissions=True)
		return review.name
	else:
		return review_exist

def get_review():
	review = frappe.db.exists("Quality Review", {"goal": "GOAL-_Test Quality Goal"})
	return review