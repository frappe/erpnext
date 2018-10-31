# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

test_dependencies = ["Quality Procedure","Measurement Unit" ,"Quality Goal", "Quality Review"]

class TestQualityAction(unittest.TestCase):
	def test_quality_action(self):
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
	action_exist = frappe.get_list("Quality Action", filters={"name": ""+ review[0].name +""})
	if len(action_exist) == 0:
		action.insert()
		return action
	else:
		return action_exist[0]

def get_action():
	review = frappe.get_list("Quality Review")
	action = frappe.get_list("Quality Action", filters={"name": ""+ review[0].name +""})
	return action[0]