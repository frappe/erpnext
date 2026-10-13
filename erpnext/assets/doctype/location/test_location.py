# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import json

import frappe

from erpnext.assets.doctype.location.location import compute_area, get_children
from erpnext.tests.utils import ERPNextTestSuite


class TestLocation(ERPNextTestSuite):
	def test_location_features(self):
		locations = ["Basil Farm", "Division 1", "Field 1", "Block 1"]
		area = 0
		formatted_locations = []

		for location in locations:
			doc = frappe.get_doc("Location", location)
			doc.save()
			own_features = [
				feature
				for feature in json.loads(doc.location)["features"]
				if not feature["properties"].get("child_feature")
			]
			for feature in own_features:
				feature["properties"].update({"child_feature": True, "feature_of": location})
			area += compute_area(own_features)
			formatted_locations.extend(own_features)

		test_location = frappe.get_doc("Location", "Test Location Area")
		test_location.save()

		test_location_features = json.loads(test_location.get("location"))["features"]
		ordered_test_location_features = sorted(
			test_location_features, key=lambda x: x["properties"]["feature_of"]
		)
		ordered_formatted_locations = sorted(formatted_locations, key=lambda x: x["properties"]["feature_of"])

		self.assertEqual(ordered_formatted_locations, ordered_test_location_features)
		self.assertAlmostEqual(area, test_location.get("area"))

	def test_area_rolls_up_on_insert_delete_and_move(self):
		parent, other_parent = (make_location(name, is_group=1) for name in ("Area Parent", "Area Other"))
		child = make_location("Area Child", parent_location=parent.name, location=square(77.0))
		second_child = make_location("Area Child 2", parent_location=parent.name, location=square(78.0))
		second_child.delete()

		self.assertEqual(get_area_and_feature_count(parent.name), (child.area, 1))

		child.parent_location = other_parent.name
		child.save()

		self.assertEqual(get_area_and_feature_count(parent.name), (0, 0))
		self.assertEqual(get_area_and_feature_count(other_parent.name), (child.area, 1))

	def test_moving_a_group_moves_its_descendants_features(self):
		old_parent, new_parent = (make_location(name, is_group=1) for name in ("Move From", "Move To"))
		group = make_location("Move Group", parent_location=old_parent.name, is_group=1)
		child = make_location("Move Child", parent_location=group.name, location=square(79.0))

		group.reload()
		group.parent_location = new_parent.name
		group.save()

		self.assertEqual(get_area_and_feature_count(old_parent.name), (0, 0))
		self.assertEqual(get_area_and_feature_count(new_parent.name), (child.area, 1))
		feature = json.loads(new_parent.reload().location)["features"][0]
		self.assertEqual(feature["properties"]["feature_of"], child.location_name)

	def test_child_cannot_replace_sibling_features_in_parent(self):
		parent = make_location("Sibling Parent", is_group=1)
		sibling = make_location("Sibling A", parent_location=parent.name, location=square(80.0))
		child = make_location("Sibling B", parent_location=parent.name, location=square(81.0))

		location = json.loads(child.location)
		forged = json.loads(square(82.0))["features"][0]
		forged["properties"] = {"child_feature": True, "feature_of": sibling.name}
		location["features"].append(forged)
		child.location = json.dumps(location)
		child.save()

		features = json.loads(parent.reload().location)["features"]
		sibling_geometries = [
			f["geometry"] for f in features if f["properties"]["feature_of"] == sibling.name
		]
		self.assertEqual(sibling_geometries, [json.loads(square(80.0))["features"][0]["geometry"]])
		self.assertEqual(len(features), 3)
		self.assertAlmostEqual(parent.area, sibling.area + child.reload().area)

	def test_coordinates_out_of_range_are_refused(self):
		for coordinates in (
			{"latitude": 123.4},
			{"latitude": -90.5},
			{"longitude": -999},
			{"longitude": 180.1},
		):
			self.assertRaises(frappe.ValidationError, make_location, "Bad Coordinates", **coordinates)

		location = make_location("Edge Coordinates", latitude=-90, longitude=180)
		self.assertEqual((location.latitude, location.longitude), (-90, 180))

	def test_get_children_needs_location_permission(self):
		user = frappe.get_doc(
			{"doctype": "User", "email": "location-website-user@example.com", "first_name": "Website"}
		).insert(ignore_permissions=True)

		with self.set_user(user.name):
			self.assertRaises(frappe.PermissionError, get_children, "Location")

		self.assertTrue(get_children("Location"))


def make_location(location_name: str, **args):
	return frappe.get_doc({"doctype": "Location", "location_name": location_name, **args}).insert()


def square(longitude: float, latitude: float = 28.0, size: float = 0.01) -> str:
	ring = [
		[longitude, latitude],
		[longitude + size, latitude],
		[longitude + size, latitude + size],
		[longitude, latitude + size],
		[longitude, latitude],
	]
	feature = {"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": [ring]}}
	return json.dumps({"type": "FeatureCollection", "features": [feature]})


def get_area_and_feature_count(location: str) -> tuple[float, int]:
	doc = frappe.get_doc("Location", location)
	return doc.area, len(json.loads(doc.location or '{"features": []}')["features"])
