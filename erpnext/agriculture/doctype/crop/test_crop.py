# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

class TestCrop(unittest.TestCase):
	create_list = [
		{
			'doctype': 'Item',
			'item_code': 'Basil Seeds',
			'item_name': 'Basil Seeds',
			'item_group': 'Seed'
		},
		{
			'doctype': 'Item',
			'item_code': 'Twigs',
			'item_name': 'Twigs',
			'item_group': 'By-product'
		},
		{
			'doctype': 'Item',
			'item_code': 'Basil Leaves',
			'item_name': 'Basil Leaves',
			'item_group': 'Produce'
		},
		{
			'doctype': 'Crop',
			'common_name': 'Basil',
			'scientific_name': 'Ocimum basilicum',
			'materials_required': [{
				'item_code': 'Basil Seeds',
				'qty': '25',
				'uom': 'Nos',
				'rate': '1'
			}, {
				'item_code': 'Urea',
				'qty': '5',
				'uom': 'Kg',
				'rate': '10'
			}],
			'byproducts': [{
				'item_code': 'Twigs',
				'qty': '25',
				'uom': 'Nos',
				'rate': '1'
			}],
			'produce': [{
				'item_code': 'Basil Leaves',
				'qty': '100',
				'uom': 'Nos',
				'rate': '1'
			}],
			'agriculture_task': [{
				'subject': "Plough the field",
				'start_day': 1,
				'end_day': 1,
				'holiday_management': "Ignore holidays"
			}, {
				'subject': "Plant the seeds",
				'start_day': 2,
				'end_day': 3,
				'holiday_management': "Ignore holidays"
			}, {
				'subject': "Water the field",
				'start_day': 4,
				'end_day': 4,
				'holiday_management': "Ignore holidays"
			}, {
				'subject': "First harvest",
				'start_day': 8,
				'end_day': 8,
				'holiday_management': "Ignore holidays"
			}, {
				'subject': "Add the fertilizer",
				'start_day': 10,
				'end_day': 12,
				'holiday_management': "Ignore holidays"
			}, {
				'subject': "Final cut",
				'start_day': 15,
				'end_day': 15,
				'holiday_management': "Ignore holidays"
			}]
		}
	]

	for x in create_list:
		doc = frappe.get_doc(x)
		doc.save()
	
	basil = frappe.get_doc('Crop', 'Basil')
	self.assertEquals(basil.period, 15)