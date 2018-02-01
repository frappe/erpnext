# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
import math

from  frappe import _

from frappe.utils.nestedset import NestedSet
from frappe.utils import flt
# from frappe.model.document import Document

RADIUS = 6378137
FLATTENING_DENOM = 298.257223563
FLATTENING = 1/FLATTENING_DENOM
POLAR_RADIUS = RADIUS*(1-FLATTENING)

class LandUnit(NestedSet):
	# pass
	nsm_parent_field = 'parent_land_unit'

	def on_trash(self):
		ancestors = self.get_ancestors()
		for ancestor in ancestors:
			ancestor_doc = frappe.get_doc('Land Unit', ancestor)	
			ancestor_child_features, ancestor_non_child_features = ancestor_doc.feature_seperator(child_feature = self.get('land_unit_name'))
			ancestor_features = ancestor_non_child_features
			for index,feature in enumerate(ancestor_features):
				ancestor_features[index] = json.loads(feature)
			ancestor_doc.set_location_value(features = ancestor_features)	
			ancestor_doc.db_set(fieldname='area', value=ancestor_doc.get('area')-self.get('area'),commit=True)
		super(LandUnit, self).on_update()

	def validate(self):
		if not self.is_new():
			if not self.get('location'):
				features = ''
			else:
				features = json.loads(self.get('location')).get('features')
			new_area = compute_area(features)
			self.area_difference = new_area - flt(self.area)
			self.area = new_area	

			if self.get('parent_land_unit'):
				ancestors = self.get_ancestors()
				self_features = self.add_child_property()
				self_features = set(self_features)

				for ancestor in ancestors:
					ancestor_doc = frappe.get_doc('Land Unit', ancestor)
					ancestor_child_features, ancestor_non_child_features = ancestor_doc.feature_seperator(child_feature = self.get('land_unit_name'))
					ancestor_features = list(set(ancestor_non_child_features))
					child_features = set(ancestor_child_features)

					if not (self_features.issubset(child_features) and child_features.issubset(self_features)): 
						features_to_be_appended =	self_features - child_features 
						features_to_be_discarded = 	child_features - self_features
						for feature in features_to_be_discarded:
							child_features.discard(feature)
						for feature in features_to_be_appended:
							child_features.add(feature)
						child_features = list(child_features)

					ancestor_features.extend(child_features)
					for index,feature in enumerate(ancestor_features):
						ancestor_features[index] = json.loads(feature)
					ancestor_doc.set_location_value(features = ancestor_features)	
					ancestor_doc.db_set(fieldname='area', value=ancestor_doc.get('area')+\
						self.get('area_difference'),commit=True)

	def set_location_value(self, features):
		if not self.get('location'):
			self.location = '{"type":"FeatureCollection","features":[]}'
		location = json.loads(self.location)
		location['features'] = features
		self.db_set(fieldname='location', value=json.dumps(location), commit=True)

	def on_update(self):
		super(LandUnit, self).on_update()

	def add_child_property(self):
		location = self.get('location')
		if location:
			features = json.loads(location).get('features')	
			if type(features) != list:
				features = json.loads(features)
			filter_features = [feature for feature in features if feature.get('properties').get('child_feature') != True]
			for index,feature in enumerate(filter_features):
				feature['properties'].update({'child_feature': True, 'feature_of': self.land_unit_name})
				filter_features[index] = json.dumps(filter_features[index])
			return filter_features 
		return []

	def feature_seperator(self, child_feature=None):
		doc = self 
		child_features = []
		non_child_features = []
		location = doc.get('location')
		if location:
			features = json.loads(location).get('features')
			if type(features) != list:
				features = json.loads(features)
			for feature in features:
				if feature.get('properties').get('feature_of') == child_feature:
					child_features.extend([json.dumps(feature)])
				else:
					non_child_features.extend([json.dumps(feature)])
		
		return child_features, non_child_features


def compute_area(features):                                
	layer_area = 0
	for feature in features:
		if feature.get('geometry').get('type') == 'Polygon':
			layer_area += polygon_area(coords = feature.get('geometry').get('coordinates'))
		elif feature.get('geometry').get('type') == 'Point' and feature.get('properties').get('point_type') == 'circle':
			layer_area += math.pi * math.pow(feature.get('properties').get('radius'), 2)
	return flt(layer_area)

def rad(angle_in_degrees):
	return angle_in_degrees*math.pi/180

def polygon_area(coords):
	area = 0
	if coords and len(coords) > 0:
		area += math.fabs(ring_area(coords[0]));
		for i in range(1, len(coords)): 
			area -= math.fabs(ring_area(coords[i]));
	return area;
	
def ring_area(coords):
	p1 = 0
	p2 = 0
	p3 = 0
	lower_index = 0
	middle_index = 0
	upper_index = 0
	i = 0
	area = 0
	coords_length = len(coords)
	if coords_length > 2: 
		for i in range(0, coords_length):
			if i == coords_length - 2: # i = N-2
				lower_index = coords_length - 2;
				middle_index = coords_length -1;
				upper_index = 0;
			elif i == coords_length - 1: # i = N-1
				lower_index = coords_length - 1;
				middle_index = 0;
				upper_index = 1;
			else: # i = 0 to N-3
				lower_index = i;
				middle_index = i+1;
				upper_index = i+2;
			p1 = coords[lower_index];
			p2 = coords[middle_index];
			p3 = coords[upper_index];
			area += ( rad(p3[0]) - rad(p1[0]) ) * math.sin( rad(p2[1]));

		area = area * RADIUS * RADIUS / 2
	return area

@frappe.whitelist()
def get_children(doctype, parent, is_root=False):
	if is_root:
		parent = ''

	land_units = frappe.db.sql("""select name as value,
		is_group as expandable
		from `tabLand Unit`
		where ifnull(`parent_land_unit`,'') = %s
		order by name""", (parent), as_dict=1)

	# return nodes
	return land_units
		