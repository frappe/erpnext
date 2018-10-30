# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

class TestQualityGoal(unittest.TestCase):
	
	def test_quality_goal(self):
		test_create_goal = create_goal()
		test_get_goal = get_goal()
		self.assertEquals(test_create_goal.name, test_get_goal.name)

def create_goal():
	goal = frappe.get_doc({
		"doctype": "Quality Goal",
		"goal": "_Test Quality Goal",
		"revision": "1",
		"frequency": "Daily",
		"measureable": "Yes",
		"objective": [
			{
				"objective": "_Test Quality Objective",
				"target": "4"
			}
		]
	})
	goal_exist = frappe.get_list("Quality Goal", filters={"goal": ""+ goal.goal +""}, fields=["name"])
	if len(goal_exist) == 0:
		goal.insert()
		return goal
	else:
		return goal_exist[0]

@frappe.whitelist()
def get_goal():
	goal = frappe.get_list("Quality Goal", filters={"goal": "_Test Quality Goal"}, fields=["name"])
	return goal[0]