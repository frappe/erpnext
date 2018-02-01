# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

test_dependencies = ["Crop", "Fertilizer", "Land Unit", "Disease"]

class TestCropCycle(unittest.TestCase):
	def test_crop_cycle_creation(self):
		cycle = frappe.get_doc('Crop Cycle', 'Basil from seed 2017')
		self.assertEquals(frappe.db.exists('Crop Cycle', 'Basil from seed 2017'), 'Basil from seed 2017')

		# check if the tasks were created 
		self.assertEquals(check_task_creation(), True)
		self.assertEquals(check_project_creation(), True)

def check_task_creation():
	all_task_dict = {
		"Survey and find the aphid locations": {
			"exp_start_date": frappe.utils.datetime.date(2017,11,21),
			"exp_end_date": frappe.utils.datetime.date(2017,11,22)
		},
		"Apply Pesticides": {
			"exp_start_date": frappe.utils.datetime.date(2017,11,23),
			"exp_end_date": frappe.utils.datetime.date(2017,11,23)
		},
		"Plough the field": {
			"exp_start_date": frappe.utils.datetime.date(2017,11,11),
			"exp_end_date": frappe.utils.datetime.date(2017,11,11)
		},
		"Plant the seeds": {
			"exp_start_date": frappe.utils.datetime.date(2017,11,12),
			"exp_end_date": frappe.utils.datetime.date(2017,11,13)
		},
		"Water the field": {
			"exp_start_date": frappe.utils.datetime.date(2017,11,14),
			"exp_end_date": frappe.utils.datetime.date(2017,11,14)
		},
		"First harvest": {
			"exp_start_date": frappe.utils.datetime.date(2017,11,18),
			"exp_end_date": frappe.utils.datetime.date(2017,11,18)
		},
		"Add the fertilizer": {
			"exp_start_date": frappe.utils.datetime.date(2017,11,20),
			"exp_end_date": frappe.utils.datetime.date(2017,11,22)
		},
		"Final cut":{
			"exp_start_date": frappe.utils.datetime.date(2017,11,25),
			"exp_end_date": frappe.utils.datetime.date(2017,11,25)
		}
	}
	all_tasks = frappe.get_all('Task')
	for task in all_tasks:
		sample_task = frappe.get_doc('Task', task.name)
		if sample_task.subject in all_task_dict.keys():
			if sample_task.exp_start_date != all_task_dict[sample_task.subject]['exp_start_date'] or sample_task.exp_end_date != all_task_dict[sample_task.subject]['exp_end_date']:
				return False
			all_task_dict.pop(sample_task.subject)
	if all_task_dict != {}:
		return False
	return True

def check_project_creation():
	if frappe.db.exists('Project', 'Basil from seed 2017'): return True
	else: return False