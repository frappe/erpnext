# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals
import json
import frappe
import unittest

class TestLandUnit(unittest.TestCase):
<<<<<<< 8656148667bf5dfb1fed066a1fa89420c5d10de1
	def test_texture_selection(self):
		self.assertEquals(frappe.db.exists('Land Unit', 'Basil Farm'), 'Basil Farm')
=======

	def runTest(self):
		land_units = ['Basil Farm', 'Division 1', 'Field 1', 'Block 1']
		parent_land_units = ['All Land Units']
		parent_land_units.extend(land_units[0:3])
		locations = ['{"type":"FeatureCollection","features":[{"type":"Feature","properties":{"point_type":"circle","radius":884.5625420736483},"geometry":{"type":"\
Point","coordinates":[72.875834,19.100566]}}]}', '{"type":"FeatureCollection","features":[{"type":"Feature","properties":{"point_type":"circle","radius":542.342\
4997060739},"geometry":{"type":"Point","coordinates":[72.852359,19.11557]}}]}', '{"type":"FeatureCollection","features":[{"type":"Feature","properties":{},"geom\
etry":{"type":"Polygon","coordinates":[[[72.846758,19.118287],[72.846758,19.121206],[72.850535,19.121206],[72.850535,19.118287],[72.846758,19.118287]]]}}]}', '{\
"type":"FeatureCollection","features":[{"type":"Feature","properties":{},"geometry":{"type":"Polygon","coordinates":[[[72.921495,19.073313],[72.924929,19.068121\
],[72.934713,19.06585],[72.929392,19.05579],[72.94158,19.056926],[72.951365,19.095213],[72.921495,19.073313]]]}}]}']
		area = 0                                                             
		for land_unit_tuple in zip(land_units, parent_land_units, locations):
			doc = frappe.new_doc('Land Unit')                                                                                                               
			r = {'land_unit_name': land_unit_tuple[0], 'parent_land_unit': land_unit_tuple[1], 'parent': land_unit_tuple[1], 'location': land_unit_tuple[2], 'is_container': 1, 'is_group': 1}
			if land_unit_tuple[0] == 'Block 1':
				r['is_group'] = 0
			doc.update(r) 
			doc.insert()
			frappe.db.commit()
			doc.save()
			area += doc.get('area') 
		formatted_land_units = []	
		for location_tuple in zip(land_units, locations):
			temp = json.loads(location_tuple[1])
			temp['features'][0]['properties']['child_feature'] = True
			temp['features'][0]['properties']['feature_of'] =	location_tuple[0] 
			formatted_land_units.extend(temp['features'])
		formatted_land_unit_string = str(formatted_land_units)
		all_land_units = frappe.get_doc('Land Unit', 'All Land Units')
		assert formatted_land_unit_string == str(json.loads(all_land_units.get('location'))['features'])
		assert area == all_land_units.get('area')

#	Sample Features considered for testing land unit
# Block 1 location 
# '{"type":"FeatureCollection","features":[{"type":"Feature","properties":{},"geometry":{"type":"Polygon","coordinates":[[[72.921495,19.073313],[72.924929,19.068121],[72.934713,19.06585],[72.929392,19.05579],[72.94158,19.056926],[72.951365,19.095213],[72.921495,19.073313]]]}}]}'
# Area = 59,85,835.366

# Field 1 location 
# '{"type":"FeatureCollection","features":[{"type":"Feature","properties":{},"geometry":{"type":"Polygon","coordinates":[[[72.846758,19.118287],[72.846758,19.121206],[72.850535,19.121206],[72.850535,19.118287],[72.846758,19.118287]]]}}]}'
# Area = 1,29,086.246

# Division 1 location
# '{"type":"FeatureCollection","features":[{"type":"Feature","properties":{"point_type":"circle","radius":542.3424997060739},"geometry":{"type":"Point","coordinates":[72.852359,19.11557]}}]}'
# Area = 9,24,053.571

# Schrute Farms location 
# '{"type":"FeatureCollection","features":[{"type":"Feature","properties":{"point_type":"circle","radius":884.5625420736483},"geometry":{"type":"Point","coordinates":[72.875834,19.100566]}}]}'
# Area = 24,58,141.970
>>>>>>> Land Units tests added and area aggregation code migrated to server side
