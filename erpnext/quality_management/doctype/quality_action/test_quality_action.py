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
		self.assertEquals(test_create_action.name, test_get_action.name)

def create_action():
	review = frappe.get_list("Quality Review")
	action = frappe.get_doc({
		'doctype': 'Quality Action',
		'action': 'Corrective',
		'type': 'Quality Review',
		'review': ''+ review[0].name +'',
		'date': ''+ frappe.utils.nowdate() +'',
		'procedure': '_Test Quality Procedure'
	})
	action_exist = frappe.get_list("Quality Action", filters={"review": ""+ review[0].name +""}, limit=1)
	if len(action_exist) == 0:
		action.insert()
		return action
	else:
		return action_exist[0]

def get_action():
	review = frappe.get_list("Quality Review", limit=1)
	action = frappe.get_list("Quality Action", filters={"review": ""+ review[0].name +""}, limit=1)
	return action[0]