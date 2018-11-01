# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

class TestQualityReview(unittest.TestCase):

	def test_quality_review(self):
		create_procedure()
		create_unit()
		create_goal()
		test_create_review = create_review()
		test_get_review = get_review()
		self.assertEquals(test_create_review.name, test_get_review.name)

def create_review():
	review = frappe.get_doc({
		"doctype": "Quality Review",
		"goal": "_Test Quality Goal 1",
		"procedure": "_Test Quality Procedure 1",
		"scope": "Company",
		"date": ""+ frappe.utils.nowdate() +"",
		"values": [
			{
				"objective": "_Test Quality Objective",
				"target": "100",
				"achieved": "100",
				"unit": "_Test Unit"
			}
		]
	})
	review_exist = frappe.get_list("Quality Review", filters={"goal": "_Test Quality Goal 1"})
	if len(review_exist) == 0:
		review.insert()
		return review
	else:
		return review_exist[0]

def get_review():
	review = frappe.get_list("Quality Review", filters={"goal": "_Test Quality Goal 1"})
	return review[0]

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
		"doctype": "Measurement Unit",
		"unit": "_Test Unit 1"
	})
	unit_exist = frappe.get_list("Measurement Unit", filters={"unit": ""+ unit.unit +""}, fields=["name"])
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
				"unit": "_Test Unit 1"
			}
		]
	})
	goal_exist = frappe.get_list("Quality Goal", filters={"goal": ""+ goal.goal +""}, fields=["name"])
	if len(goal_exist) == 0:
		goal.insert()