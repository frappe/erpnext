# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

class TestPest(unittest.TestCase):
	create_list = [
		{
			'doctype': 'Pest',
			'common_name': 'Aphids',
			'scientific_name': 'Aphidoidea',
			'treatment_task': [{
				'subject': "Survey and find the aphid locations",
				'start_day': 1,
				'end_day': 2,
				'holiday_management': "Ignore holidays"
			}, {
				'subject': "Apply Pesticides",
				'start_day': 3,
				'end_day': 3,
				'holiday_management': "Ignore holidays"
			}]
		}
	]

	for x in create_list:
		doc = frappe.get_doc(x)
		doc.save()
	
	pest = frappe.get_doc('Pest', 'Aphids')
	self.assertEquals(pest.treatment_period, 3)