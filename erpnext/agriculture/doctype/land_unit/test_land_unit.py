# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals
import json
import frappe
import unittest

class TestLandUnit(unittest.TestCase):

	def runTest(self):
		land_units = ['Basil Farm', 'Division 1', 'Field 1', 'Block 1']
		area = 0                                                             
		formatted_land_units = []	
		for land_unit in land_units:
			doc = frappe.get_doc('Land Unit', land_unit)
			doc.save()
			area += doc.area
			temp = json.loads(doc.location)
			temp['features'][0]['properties']['child_feature'] = True
			temp['features'][0]['properties']['feature_of'] =	land_unit 
			formatted_land_units.extend(temp['features'])
		formatted_land_unit_string = str(formatted_land_units)
		test_land = frappe.get_doc('Land Unit', 'Test Land')
		self.assertEquals(formatted_land_unit_string, str(json.loads(test_land.get('location'))['features']))
		self.assertEquals(area, test_land.get('area'))
