# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import json

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestLocation(ERPNextTestSuite):
	def test_location_features(self):
		locations = ["Basil Farm", "Division 1", "Field 1", "Block 1"]
		area = 0
		formatted_locations = []

		for location in locations:
			doc = frappe.get_doc("Location", location)
			doc.save()
			area += doc.area
			temp = json.loads(doc.location)
			temp["features"][0]["properties"]["child_feature"] = True
			temp["features"][0]["properties"]["feature_of"] = location
			formatted_locations.extend(temp["features"])

		test_location = frappe.get_doc("Location", "Test Location Area")
		test_location.save()

		test_location_features = json.loads(test_location.get("location"))["features"]
		ordered_test_location_features = sorted(
			test_location_features, key=lambda x: x["properties"]["feature_of"]
		)
		ordered_formatted_locations = sorted(formatted_locations, key=lambda x: x["properties"]["feature_of"])

		self.assertEqual(ordered_formatted_locations, ordered_test_location_features)
		self.assertEqual(area, test_location.get("area"))

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
