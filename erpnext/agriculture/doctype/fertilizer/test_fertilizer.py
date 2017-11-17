# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

class TestFertilizer(unittest.TestCase):
	def test_fertilizer_creation(self):
		create_list = [
			{
				'doctype': 'Item',
				'item_code': 'Urea',
				'item_name': 'Urea',
				'item_group': 'Fertilizer'
			},
			{
				'doctype': 'Fertilizer',
				'fertilizer_name': 'Urea',
				'item': 'Urea'
			}
		]

		for x in create_list:
			doc = frappe.get_doc(x)
			doc.save()
		
		self.assertEquals(frappe.db.exists('Fertilizer', 'Urea'), 'Urea')