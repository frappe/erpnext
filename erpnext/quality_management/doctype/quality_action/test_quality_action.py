# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.quality_management.doctype.quality_procedure.test_quality_procedure import create_procedure
from erpnext.quality_management.doctype.quality_goal.test_quality_goal import create_unit
from erpnext.quality_management.doctype.quality_goal.test_quality_goal import create_goal
from erpnext.quality_management.doctype.quality_review.test_quality_review import create_review

class TestQualityAction(unittest.TestCase):

	def test_quality_action(self):
		create_procedure()
		create_unit()
		create_goal()
		review = create_review()
		test_create_action = create_action(review)
		test_get_action = get_action(review)

		self.assertEquals(test_create_action, test_get_action)

def create_action(review=None):
	action = frappe.get_doc({
		"doctype": "Quality Action",
		"action": "Corrective",
		"type": "Quality Review",
		"review": frappe.db.get_value("Quality Review", review, "name"),
		"date": frappe.utils.today(),
		"action_taken": "Test Action"
	})
	action_exist = frappe.db.get_value("Quality Action", {"review": review}, "name")
	if not action_exist:
		action.insert(ignore_permissions=True)
		return action.name
	else:
		return action_exist

def get_action(review=None):
	return frappe.db.get_value("Quality Action", {"review": review}, "name")