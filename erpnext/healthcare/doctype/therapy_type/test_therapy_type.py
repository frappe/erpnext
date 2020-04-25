# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

class TestTherapyType(unittest.TestCase):
	def test_therapy_type_item(self):
		therapy_type = create_therapy_type()
		self.assertTrue(frappe.db.exists('Item', therapy_type.item))

		therapy_type.disabled = 1
		therapy_type.save()
		self.assertEquals(frappe.db.get_value('Item', therapy_type.item, 'disabled'), 1)

def create_therapy_type():
	exercise = create_exercise_type()
	therapy_type = frappe.db.exists('Therapy Type', 'Basic Rehab')
	if not therapy_type:
		therapy_type = frappe.new_doc('Therapy Type')
		therapy_type.therapy_type = 'Basic Rehab'
		therapy_type.default_duration = 30
		therapy_type.is_billable = 1
		therapy_type.rate = 5000
		therapy_type.item_code = 'Basic Rehab'
		therapy_type.item_name = 'Basic Rehab'
		therapy_type.item_group = 'Services'
		therapy_type.append('exercises', {
			'exercise_type': exercise.name,
			'counts_target': 10,
			'assistance_level': 'Passive'
		})
		therapy_type.save()
	else:
		therapy_type = frappe.get_doc('Therapy Type', 'Basic Rehab')
	return therapy_type

def create_exercise_type():
	exercise_type = frappe.db.exists('Exercise Type', 'Sit to Stand')
	if not exercise_type:
		exercise_type = frappe.new_doc('Exercise Type')
		exercise_type.exercise_name = 'Sit to Stand'
		exercise_type.append('steps_table', {
			'title': 'Step 1',
			'description': 'Squat and Rise'
		})
		exercise_type.save()
	return exercise_type