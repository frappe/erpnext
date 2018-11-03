# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

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
		'procedure': '_Test Quality Procedure 1'
	})
	action_exist = frappe.get_list("Quality Action", filters={"review": ""+ review[0].name +""})
	if len(action_exist) == 0:
		action.insert()
		return action
	else:
		return action_exist[0]

def get_action():
	review = frappe.get_list("Quality Review")
	action = frappe.get_list("Quality Action", filters={"review": ""+ review[0].name +""})
	return action[0]

def create_procedure():
	procedure = frappe.get_doc({
		"doctype": "Quality Procedure",
		"procedure": "_Test Quality Procedure 1",
		"procedure_step": [
			{
				"step": "_Test Quality Procedure Table 1"
			}
		]
	})
	procedure_exist = frappe.get_list("Quality Procedure", filters={"procedure": ""+ procedure.procedure +""})
	if len(procedure_exist) == 0:
		procedure.insert()

def create_unit():
	unit = frappe.get_doc({
		"doctype": "UOM",
		"uom_name": "_Test UOM",
	})
	unit_exist = frappe.get_list("UOM", filters={"uom_name": ""+ unit.uom_name +""}, fields=["name"])
	if len(unit_exist) == 0:
		unit.insert()

def create_goal():
	goal = frappe.get_doc({
		"doctype": "Quality Goal",
		"goal": "_Test Quality Goal 1",
		"procedure": "_Test Quality Procedure 1",
		"revision": "1",
		"frequency": "None",
		"measurable": "Yes",
		"objective": [
			{
				"objective": "_Test Quality Objective 1",
				"target": "100",
				"unit": "_Test UOM"
			}
		]
	})
	goal_exist = frappe.get_list("Quality Goal", filters={"goal": ""+ goal.goal +""}, fields=["name"])
	if len(goal_exist) == 0:
		goal.insert()

def create_review():
	review = frappe.get_doc({
		"doctype": "Quality Review",
		"scope": "Company",
		"goal": "_Test Quality Goal 1",
		"procedure": "_Test Quality Procedure 1",
		"date": ""+ frappe.utils.nowdate() +"",
		"values": [
			{
				"objective": "_Test Quality Objective 1",
				"target": "100",
				"achieved": "4",
				"unit": "_Test UOM"
			}
		]
	})
	review_exist = frappe.get_list("Quality Review", filters={"goal": "_Test Quality Goal 1"})
	if len(review_exist) == 0:
		review.insert()