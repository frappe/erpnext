# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json

from  frappe import _

from frappe.utils.nestedset import NestedSet
# from frappe.model.document import Document

class LandUnit(NestedSet):
	# pass
	nsm_parent_field = 'parent_land_unit'

	def validate(self):
		if self.get('parent') and not self.is_new():
			
			ancestors = self.get_ancestors()
			self_features = self.add_child_property()	
			parent_child_features, parent_non_child_features = self.feature_seperator(feature_of = self.get('parent'))

			self_features = set(self_features)
			child_features = set(parent_child_features)

			if not (self_features.issubset(child_features) and child_features.issubset(self_features)): 
				features_to_be_appended =	self_features - child_features 
				features_to_be_discarded = 	child_features - self_features
				for feature in features_to_be_discarded:
					child_features.discard(feature)
				for feature in features_to_be_appended:
					child_features.add(feature)
				child_features = list(child_features)

				for ancestor in ancestors:
					ancestor_child_features, ancestor_non_child_features = self.feature_seperator(feature_of = ancestor)
					ancestor_features = ancestor_non_child_features
					ancestor_features.extend(child_features)
					print(ancestor_features)
					for index,feature in enumerate(ancestor_features):
						ancestor_features[index] = json.loads(feature)
					ancestor_doc = frappe.get_doc('Land Unit', ancestor)	
					ancestor_doc.set_location_value(features = ancestor_features)	

	def set_location_value(self, features):
		if not self.get('location'):
			self.location = '{"type":"FeatureCollection","features":[]}'
		location = json.loads(self.location)
		location['features'] = features
		self.db_set(fieldname='location', value=json.dumps(location), commit=True)

	def on_update(self):
		super(LandUnit, self).on_update()
		self.validate_one_root()

	def add_child_property(self):
		location = self.get('location')
		if location:
			features = json.loads(location).get('features')	
			if type(features) != list:
				features = json.loads(features)
			for index,feature in enumerate(features):
				if not feature.get('properties'):
					feature['properties'].update({'child_feature': True, 'feature_of': self.land_unit_name})
				features[index] = json.dumps(feature)
			return features 
		return []

	def feature_seperator(self, feature_of=None):
		doc = frappe.get_doc('Land Unit', feature_of)
		child_features = []
		non_child_features = []
		location = doc.get('location')
		if location:
			features = json.loads(location).get('features')
			if type(features) != list:
				features = json.loads(features)
			for feature in features:
				if feature.get('properties').get('feature_of') == self.get('land_unit_name'):
					child_features.extend([json.dumps(feature)])
				else:
					non_child_features.extend([json.dumps(feature)])
		
		return child_features, non_child_features