# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import json
import math

import frappe
from frappe import _
from frappe.utils import flt
from frappe.utils.nestedset import NestedSet, get_descendants_of, update_nsm

EARTH_RADIUS = 6378137


class Location(NestedSet):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		area: DF.Float
		area_uom: DF.Link | None
		is_container: DF.Check
		is_group: DF.Check
		latitude: DF.Float
		lft: DF.Int
		location_name: DF.Data
		longitude: DF.Float
		old_parent: DF.Data | None
		parent_location: DF.Link | None
		rgt: DF.Int
	# end: auto-generated types

	nsm_parent_field = "parent_location"

	def validate(self):
		self.validate_coordinates()
		self.calculate_location_area()
		self.previous_ancestors = [] if self.is_new() else self.get_ancestors()

	def on_update(self):
		NestedSet.on_update(self)
		self.update_ancestor_location_features()

	def on_trash(self):
		NestedSet.validate_if_child_exists(self)
		ancestors = self.get_ancestors()
		update_nsm(self)
		for ancestor in ancestors:
			set_features_in_ancestor(ancestor, {self.location_name}, [])

	def validate_coordinates(self):
		if abs(flt(self.latitude)) > 90:
			frappe.throw(_("Latitude must be between -90 and 90"))
		if abs(flt(self.longitude)) > 180:
			frappe.throw(_("Longitude must be between -180 and 180"))

	def calculate_location_area(self):
		self.area = compute_area(self.get_location_features())

	def get_location_features(self):
		if not self.location:
			return []

		features = json.loads(self.location).get("features")

		if not isinstance(features, list):
			features = json.loads(features)

		return features

	def set_location_features(self, features):
		if not self.location:
			self.location = '{"type":"FeatureCollection","features":[]}'

		location = json.loads(self.location)
		location["features"] = features

		self.db_set("location", json.dumps(location))

	def after_rename(self, old_name: str, new_name: str, merge: bool = False):
		NestedSet.after_rename(self, old_name, new_name, merge)
		self.update_ancestor_location_features(old_names={old_name})

	def update_ancestor_location_features(self, old_names: set[str] | None = None):
		"""Replace this subtree's features in ancestors, including those still tagged with `old_names`."""
		ancestors = self.get_ancestors()
		previous_ancestors = set(self.get("previous_ancestors") or []) - set(ancestors)
		if not ancestors and not previous_ancestors:
			return

		subtree, features = self.get_subtree_features()
		for ancestor in previous_ancestors:
			set_features_in_ancestor(ancestor, subtree, [])
		for ancestor in ancestors:
			set_features_in_ancestor(ancestor, subtree | (old_names or set()), features)

	def get_subtree_features(self) -> tuple[set[str], list[dict]]:
		descendants = get_descendants_of(self.doctype, self.name, ignore_permissions=True)
		subtree = {self.name, *descendants}
		features = self.get_own_features(subtree)
		for descendant in descendants:
			features.extend(frappe.get_doc("Location", descendant).get_own_features(subtree))

		return subtree, features

	def get_own_features(self, subtree: set[str]) -> list[dict]:
		"""Return the features drawn on this location, skipping those rolled up from other `subtree` locations.

		Rolled-up features are read from each descendant's saved map, so editing them here has no effect.
		"""
		features = []
		for feature in self.get_location_features():
			if feature.get("properties").get("feature_of") in subtree - {self.name}:
				continue
			feature["properties"].update({"child_feature": True, "feature_of": self.location_name})
			features.append(feature)

		return features


def set_features_in_ancestor(ancestor: str, subtree: set[str], features: list[dict]):
	"""Replace the features of the `subtree` locations in the ancestor and recompute the ancestor's area."""
	ancestor_doc = frappe.get_doc("Location", ancestor)
	ancestor_features = [
		feature
		for feature in ancestor_doc.get_location_features()
		if feature.get("properties").get("feature_of") not in subtree
	]
	ancestor_features.extend(features)

	ancestor_doc.set_location_features(features=ancestor_features)
	ancestor_doc.db_set("area", compute_area(ancestor_features))


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
		feature_type = feature.get("geometry", {}).get("type")

		if feature_type == "Polygon":
			layer_area += _polygon_area(coords=feature.get("geometry").get("coordinates"))
		elif feature_type == "Point" and feature.get("properties").get("point_type") == "circle":
			layer_area += math.pi * math.pow(feature.get("properties").get("radius"), 2)

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
def get_children(doctype: str, parent: str | None = None, location: str | None = None, is_root: bool = False):
	if parent is None or parent == "All Locations":
		parent = ""

	frappe.has_permission("Location", throw=True)
	filters = {"parent_location": parent} if parent else {"parent_location": ["is", "not set"]}

	return frappe.get_list(
		"Location",
		filters=filters,
		fields=["name as value", "is_group as expandable"],
	)


@frappe.whitelist(methods=["POST"])
def add_node():
	from frappe.desk.treeview import make_tree_args

	args = frappe.form_dict
	args = make_tree_args(**args)

	if args.parent_location == "All Locations":
		args.parent_location = None

	frappe.get_doc(args).insert()


def on_doctype_update():
	frappe.db.add_index("Location", ["lft", "rgt"])
