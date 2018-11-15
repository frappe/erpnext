# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import json
import math

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt
from frappe.utils.nestedset import NestedSet, update_nsm

EARTH_RADIUS = 6378137


class Location(NestedSet):
	nsm_parent_field = 'parent_location'

	def validate(self):
		self.calculate_location_area()

		if not self.is_new() and self.get('parent_location'):
			self.update_ancestor_location_features()

	def on_update(self):
		# super(Location, self).on_update()
		NestedSet.on_update(self)

	def on_trash(self):
		NestedSet.validate_if_child_exists(self)
		update_nsm(self)
		self.remove_ancestor_location_features()
		# super(Location, self).on_update()

	def calculate_location_area(self):
		features = self.get_location_features()
		new_area = compute_area(features)

		self.area_difference = new_area - flt(self.area)
		self.area = new_area

	def get_location_features(self):
		if not self.location:
			return []

		features = json.loads(self.location).get('features')

		if not isinstance(features, list):
			features = json.loads(features)

		return features

	def set_location_features(self, features):
		if not self.location:
			self.location = '{"type":"FeatureCollection","features":[]}'

		location = json.loads(self.location)
		location['features'] = features

		self.db_set('location', json.dumps(location), commit=True)

	def update_ancestor_location_features(self):
		self_features = set(self.add_child_property())

		for ancestor in self.get_ancestors():
			ancestor_doc = frappe.get_doc('Location', ancestor)
			child_features, ancestor_features = ancestor_doc.feature_seperator(child_feature=self.name)

			ancestor_features = list(set(ancestor_features))
			child_features = set(child_features)

			if self_features != child_features:
				features_to_be_appended = self_features - child_features
				features_to_be_discarded = child_features - self_features

				for feature in features_to_be_discarded:
					child_features.discard(feature)

				for feature in features_to_be_appended:
					child_features.add(feature)

			ancestor_features.extend(list(child_features))

			for index, feature in enumerate(ancestor_features):
				ancestor_features[index] = json.loads(feature)

			ancestor_doc.set_location_features(features=ancestor_features)
			ancestor_doc.db_set('area', ancestor_doc.area + self.area_difference, commit=True)

	def remove_ancestor_location_features(self):
		for ancestor in self.get_ancestors():
			ancestor_doc = frappe.get_doc('Location', ancestor)
			child_features, ancestor_features = ancestor_doc.feature_seperator(child_feature=self.name)

			for index, feature in enumerate(ancestor_features):
				ancestor_features[index] = json.loads(feature)

			ancestor_doc.set_location_features(features=ancestor_features)
			ancestor_doc.db_set('area', ancestor_doc.area - self.area, commit=True)

	def add_child_property(self):
		features = self.get_location_features()
		filter_features = [feature for feature in features if not feature.get('properties').get('child_feature')]

		for index, feature in enumerate(filter_features):
			feature['properties'].update({'child_feature': True, 'feature_of': self.location_name})
			filter_features[index] = json.dumps(filter_features[index])

		return filter_features

	def feature_seperator(self, child_feature=None):
		child_features, non_child_features = [], []
		features = self.get_location_features()

		for feature in features:
			if feature.get('properties').get('feature_of') == child_feature:
				child_features.extend([json.dumps(feature)])
			else:
				non_child_features.extend([json.dumps(feature)])

		return child_features, non_child_features


def compute_area(features):
	"""
	Calculate the total area for a set of location features.
	Reference from https://github.com/scisco/area.

	Args:
		`features` (list of dict): Features marked on the map as
			GeoJSON data

	Returns:
		float: The approximate signed geodesic area (in sq. meters)
	"""

	layer_area = 0.0

	for feature in features:
		feature_type = feature.get('geometry', {}).get('type')

		if feature_type == 'Polygon':
			layer_area += _polygon_area(coords=feature.get('geometry').get('coordinates'))
		elif feature_type == 'Point' and feature.get('properties').get('point_type') == 'circle':
			layer_area += math.pi * math.pow(feature.get('properties').get('radius'), 2)

	return layer_area


def _polygon_area(coords):
	if not coords:
		return 0

	area = abs(_ring_area(coords[0]))

	for i in range(1, len(coords)):
		area -= abs(_ring_area(coords[i]))

	return area


def _ring_area(coords):
	area = 0.0
	coords_length = len(coords)

	if coords_length > 2:
		for i in range(coords_length):
			if i == coords_length - 2:  # i = N-2
				lower_index = coords_length - 2
				middle_index = coords_length - 1
				upper_index = 0
			elif i == coords_length - 1:  # i = N-1
				lower_index = coords_length - 1
				middle_index = 0
				upper_index = 1
			else:  # i = 0 to N-3
				lower_index = i
				middle_index = i + 1
				upper_index = i + 2

			p1 = coords[lower_index]
			p2 = coords[middle_index]
			p3 = coords[upper_index]
			area += (math.radians(p3[0]) - math.radians(p1[0])) * math.sin(math.radians(p2[1]))

		area = area * EARTH_RADIUS * EARTH_RADIUS / 2

	return area


@frappe.whitelist()
def get_children(doctype, parent=None, location=None, is_root=False):
	if parent is None or parent == "All Locations":
		parent = ""

	return frappe.db.sql("""
		select
			name as value,
			is_group as expandable
		from
			`tab{doctype}` comp
		where
			ifnull(parent_location, "")={parent}
		""".format(
			doctype=doctype,
			parent=frappe.db.escape(parent)
		), as_dict=1)

@frappe.whitelist()
def add_node():
	from frappe.desk.treeview import make_tree_args
	args = frappe.form_dict
	args = make_tree_args(**args)

	if args.parent_location == 'All Locations':
		args.parent_location = None

	frappe.get_doc(args).insert()


def on_doctype_update():
	frappe.db.add_index("Location", ["lft", "rgt"])

@frappe.whitelist()
def get_total_location():
	# Get the total of all locations in square meters
	total_location = frappe.db.get_value("Location", {"is_group": 0}, "sum(round(area, 3))")

	return total_location
