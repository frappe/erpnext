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
		create_review()
		test_create_action = create_action()
		test_get_action = get_action()

		self.assertEquals(test_create_action, test_get_action)

def create_action():
	review = frappe.db.exists("Quality Review", {"goal": "GOAL-_Test Quality Goal"})
	action = frappe.get_doc({
		"doctype": "Quality Action",
		"action": "Corrective",
		"document_type": "Quality Review",
		"document_name": review,
		"date": frappe.utils.nowdate(),
		"goal": "GOAL-_Test Quality Goal",
		"procedure": "PRC-_Test Quality Procedure"
	})
	action_exist = frappe.db.exists("Quality Action", {"review": review})

	if not action_exist:
		action.insert()
		return action.name
	else:
		return action_exist

def get_action():
	review = frappe.db.exists("Quality Review", {"goal": "GOAL-_Test Quality Goal"})
	return frappe.db.exists("Quality Action", {"document_name": review})