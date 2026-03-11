# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import json
import math
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from erpnext.assets.doctype.location.location import (
	_polygon_area,
	_ring_area,
	add_node,
	compute_area,
	get_children,
	on_doctype_update,
)


class TestLocation(IntegrationTestCase):
	def setUp(self):
		self.ancestor_snapshots = {}
		for location in ["Basil Farm", "Division 1", "Field 1", "Block 1", "Test Location Area"]:
			if frappe.db.exists("Location", location):
				doc = frappe.get_doc("Location", location)
				for ancestor_name in doc.get_ancestors():
					if ancestor_name not in self.ancestor_snapshots:
						ancestor_doc = frappe.get_doc("Location", ancestor_name)
						self.ancestor_snapshots[ancestor_name] = {
							"area": ancestor_doc.area,
							"location": ancestor_doc.location,
						}

		self.created_locations = []

	def tearDown(self):
		frappe.db.rollback()

		for ancestor_name, snapshot in self.ancestor_snapshots.items():
			if frappe.db.exists("Location", ancestor_name):
				frappe.db.set_value(
					"Location",
					ancestor_name,
					{
						"area": snapshot["area"],
						"location": snapshot["location"],
					},
					update_modified=False,
				)

		for name in reversed(self.created_locations):
			if frappe.db.exists("Location", name):
				frappe.delete_doc(
					"Location",
					name,
					force=True,
					ignore_permissions=True,
				)

		frappe.db.commit()

	def create_location(
		self,
		location_name,
		parent_location=None,
		area=0,
		is_group=0,
		is_container=0,
		latitude=0,
		longitude=0,
		location_geojson=None,
	):
		"""
		Helper function to create location document
		"""
		doc = frappe.get_doc(
			{
				"doctype": "Location",
				"location_name": location_name,
				"parent_location": parent_location,
				"area": area,
				"is_group": is_group,
				"is_container": is_container,
				"latitude": latitude,
				"longitude": longitude,
			}
		)
		if location_geojson:
			doc.location = location_geojson

		doc.insert(ignore_permissions=True)
		self.created_locations.append(doc.name)

		return doc

	def test_calculate_location_area_polygon(self):
		geojson = json.dumps(
			{
				"type": "FeatureCollection",
				"features": [
					{
						"type": "Feature",
						"geometry": {
							"type": "Polygon",
							"coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]],
						},
						"properties": {},
					}
				],
			}
		)

		location = self.create_location("_Test Polygon Location", location_geojson=geojson)

		self.assertGreater(location.area, 0)

	def test_calculate_location_area_circle(self):
		geojson = json.dumps(
			{
				"type": "FeatureCollection",
				"features": [
					{
						"type": "Feature",
						"geometry": {"type": "Point", "coordinates": [0, 0]},
						"properties": {"point_type": "circle", "radius": 10},
					}
				],
			}
		)

		location = self.create_location("_Test Circle Location", location_geojson=geojson)

		expected_area = math.pi * 10 * 10
		self.assertAlmostEqual(location.area, expected_area, places=2)

	def test_get_location_features(self):
		geojson = json.dumps(
			{
				"type": "FeatureCollection",
				"features": [
					{
						"type": "Feature",
						"geometry": {"type": "Point", "coordinates": [0, 0]},
						"properties": {},
					}
				],
			}
		)

		location = self.create_location("_Test Features Location", location_geojson=geojson)
		features = location.get_location_features()

		self.assertEqual(len(features), 1)
		self.assertEqual(features[0]["type"], "Feature")

	def test_get_location_features_nested_json(self):
		geojson = json.dumps(
			{
				"type": "FeatureCollection",
				"features": json.dumps(
					[
						{
							"type": "Feature",
							"geometry": {"type": "Point", "coordinates": [0, 0]},
							"properties": {},
						}
					]
				),
			}
		)

		location = self.create_location("_Test Nested JSON Location", location_geojson=geojson)
		features = location.get_location_features()

		self.assertIsInstance(features, list)
		self.assertEqual(len(features), 1)
		self.assertEqual(features[0]["type"], "Feature")

	def test_get_location_features_empty(self):
		location = self.create_location("_Test Location")
		features = location.get_location_features()

		self.assertEqual(features, [])

	def test_set_location_features(self):
		location = self.create_location("_Test Location")

		new_features = [
			{
				"type": "Feature",
				"geometry": {"type": "Point", "coordinates": [1, 1]},
				"properties": {"test": "value"},
			}
		]

		location.set_location_features(new_features)
		location.reload()

		features = location.get_location_features()
		self.assertEqual(len(features), 1)
		self.assertEqual(features[0]["properties"]["test"], "value")

	def test_add_child_property(self):
		geojson = json.dumps(
			{
				"type": "FeatureCollection",
				"features": [
					{
						"type": "Feature",
						"geometry": {"type": "Point", "coordinates": [0, 0]},
						"properties": {},
					}
				],
			}
		)

		location = self.create_location("_Test Child Property", location_geojson=geojson)
		filtered_features = location.add_child_property()

		self.assertEqual(len(filtered_features), 1)

		feature = json.loads(filtered_features[0])
		self.assertTrue(feature["properties"]["child_feature"])
		self.assertEqual(feature["properties"]["feature_of"], location.location_name)

	def test_feature_separator(self):
		geojson = json.dumps(
			{
				"type": "FeatureCollection",
				"features": [
					{
						"type": "Feature",
						"geometry": {"type": "Point", "coordinates": [0, 0]},
						"properties": {"child_feature": True, "feature_of": "Child1"},
					},
					{
						"type": "Feature",
						"geometry": {"type": "Point", "coordinates": [1, 1]},
						"properties": {},
					},
				],
			}
		)

		location = self.create_location("_Test Separator", location_geojson=geojson)
		child_features, non_child_features = location.feature_seperator("Child1")

		self.assertEqual(len(child_features), 1)
		self.assertEqual(len(non_child_features), 1)

	def test_update_ancestor_location_features(self):
		parent = self.create_location("_Test Parent Location", is_group=1)

		child_geojson = json.dumps(
			{
				"type": "FeatureCollection",
				"features": [
					{
						"type": "Feature",
						"geometry": {"type": "Point", "coordinates": [0, 0]},
						"properties": {"radius": 5, "point_type": "circle"},
					}
				],
			}
		)

		child = self.create_location(
			"Child Location", parent_location=parent.name, location_geojson=child_geojson
		)

		child.save()

		parent.reload()
		parent_features = parent.get_location_features()

		self.assertGreater(len(parent_features), 0)
		self.assertEqual(parent_features[0]["properties"]["feature_of"], "Child Location")
		self.assertTrue(parent_features[0]["properties"]["child_feature"])

	def test_update_ancestor_features_with_discarded_features(self):
		parent = self.create_location("_Test Parent Location 2", is_group=1)

		initial_geojson = json.dumps(
			{
				"type": "FeatureCollection",
				"features": [
					{
						"type": "Feature",
						"geometry": {"type": "Point", "coordinates": [0, 0]},
						"properties": {"radius": 5, "point_type": "circle", "id": "feature1"},
					},
					{
						"type": "Feature",
						"geometry": {"type": "Point", "coordinates": [1, 1]},
						"properties": {"radius": 3, "point_type": "circle", "id": "feature2"},
					},
				],
			}
		)

		child = self.create_location(
			"_Test Child Location", parent_location=parent.name, location_geojson=initial_geojson
		)
		child.save()

		parent.reload()
		self.assertEqual(len(parent.get_location_features()), 2)

		updated_geojson = json.dumps(
			{
				"type": "FeatureCollection",
				"features": [
					{
						"type": "Feature",
						"geometry": {"type": "Point", "coordinates": [2, 2]},
						"properties": {"radius": 10, "point_type": "circle", "id": "feature3"},
					}
				],
			}
		)

		child.location = updated_geojson
		child.save()

		parent.reload()
		final_features = parent.get_location_features()

		self.assertIsInstance(final_features, list)
		self.assertEqual(len(final_features), 1)
		self.assertEqual({feature["properties"]["id"] for feature in final_features}, {"feature3"})

	def test_remove_ancestor_location_features(self):
		parent = self.create_location("_Test Parent Location 3", is_group=1)

		child1_geojson = json.dumps(
			{
				"type": "FeatureCollection",
				"features": [
					{
						"type": "Feature",
						"geometry": {"type": "Point", "coordinates": [0, 0]},
						"properties": {"radius": 5, "point_type": "circle"},
					}
				],
			}
		)

		child2_geojson = json.dumps(
			{
				"type": "FeatureCollection",
				"features": [
					{
						"type": "Feature",
						"geometry": {"type": "Point", "coordinates": [1, 1]},
						"properties": {"radius": 3, "point_type": "circle"},
					}
				],
			}
		)

		child1 = self.create_location(
			"_Test Child Location 2", parent_location=parent.name, location_geojson=child1_geojson
		)
		child1.save()

		child2 = self.create_location(
			"_Test Child Location 3", parent_location=parent.name, location_geojson=child2_geojson
		)
		child2.save()

		parent.reload()
		parent_features_with_both = parent.get_location_features()
		self.assertEqual(len(parent_features_with_both), 2)

		child1_area = child1.area
		parent_area_before_delete = parent.area

		child1.delete()
		parent.reload()

		self.assertAlmostEqual(parent.area, parent_area_before_delete - child1_area, places=2)

		parent_features_after_delete = parent.get_location_features()
		self.assertEqual(len(parent_features_after_delete), 1)
		self.assertEqual(
			parent_features_after_delete[0]["properties"]["feature_of"], "_Test Child Location 3"
		)

	def test_compute_area_polygon(self):
		features = [
			{
				"geometry": {
					"type": "Polygon",
					"coordinates": [[[0, 0], [0, 0.001], [0.001, 0.001], [0.001, 0], [0, 0]]],
				},
				"properties": {},
			}
		]

		area = compute_area(features)
		self.assertGreater(area, 0)

	def test_compute_area_circle(self):
		radius = 100
		features = [
			{
				"geometry": {"type": "Point", "coordinates": [0, 0]},
				"properties": {"point_type": "circle", "radius": radius},
			}
		]

		area = compute_area(features)
		expected_area = math.pi * radius * radius
		self.assertAlmostEqual(area, expected_area, places=2)

	def test_compute_area_empty(self):
		area = compute_area([])
		self.assertEqual(area, 0.0)

	def test_polygon_area(self):
		coords = [[[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]], [[2, 2], [2, 4], [4, 4], [4, 2], [2, 2]]]

		area = _polygon_area(coords)
		self.assertGreater(area, 0)

	def test_polygon_area_empty(self):
		area = _polygon_area([])
		self.assertEqual(area, 0)

	def test_ring_area(self):
		coords = [[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]

		area = _ring_area(coords)
		self.assertIsInstance(area, float)

	def test_ring_area_small_polygon(self):
		coords = [[0, 0], [1, 1]]
		area = _ring_area(coords)
		self.assertEqual(area, 0.0)

	def test_get_children_root(self):
		root_location = self.create_location("_Test Root Location 1", is_group=1)

		children = get_children(doctype="Location", parent=None)
		self.assertIsInstance(children, list)

		child_names = [c["value"] for c in children]
		self.assertIn(root_location.name, child_names)

	def test_get_children_with_translated_root(self):
		with patch("erpnext.assets.doctype.location.location._") as mock_translate:
			mock_translate.side_effect = lambda x: "Todas las ubicaciones" if x == "All Locations" else x

			children_translated = get_children("Location", parent="Todas las ubicaciones")
			children_english = get_children("Location", parent="All Locations")
			children_empty = get_children("Location", parent="")

			# All three should return the same root-level locations
			self.assertIsInstance(children_translated, list)
			self.assertEqual(children_translated, children_english)
			self.assertEqual(children_translated, children_empty)

	def test_get_children_with_parent(self):
		parent = self.create_location("_Test Parent Location 4", is_group=1)
		child1 = self.create_location("_Test Child Location 1", parent_location=parent.name)
		child2 = self.create_location("_Test Child Location 2", parent_location=parent.name, is_group=1)

		children = get_children(doctype="Location", parent=parent.name)

		self.assertEqual(len(children), 2)
		child_names = [c["value"] for c in children]
		self.assertIn(child1.name, child_names)
		self.assertIn(child2.name, child_names)

		for child in children:
			if child["value"] == child1.name:
				self.assertEqual(child["expandable"], 0)
			elif child["value"] == child2.name:
				self.assertEqual(child["expandable"], 1)

	def test_get_children_all_locations(self):
		root_location = self.create_location("_Test Root Location 2", is_group=1)

		children = get_children(doctype="Location", parent="All Locations")
		self.assertIsInstance(children, list)

		child_names = [c["value"] for c in children]
		self.assertIn(root_location.name, child_names)

	def test_add_node(self):
		frappe.local.form_dict = frappe._dict(
			{
				"doctype": "Location",
				"location_name": "_Test New Node Location",
				"parent_location": None,
				"is_group": 1,
				"is_root": "true",
			}
		)

		add_node()

		self.assertTrue(frappe.db.exists("Location", {"location_name": "_Test New Node Location"}))

	def test_add_node_with_all_locations_parent(self):
		frappe.local.form_dict = frappe._dict(
			{
				"doctype": "Location",
				"location_name": "_Test New Node All Locations",
				"parent_location": "All Locations",
				"is_group": 1,
				"is_root": "false",
			}
		)

		add_node()

		location = frappe.get_doc("Location", {"location_name": "_Test New Node All Locations"})
		self.assertIsNone(location.parent_location)

	def test_nested_set_lft_rgt(self):
		parent = self.create_location("_Test Nested Parent", is_group=1)
		child = self.create_location("_Test Nested Child", parent_location=parent.name)

		parent.reload()
		child.reload()

		self.assertLess(parent.lft, child.lft)
		self.assertLess(child.lft, child.rgt)
		self.assertLess(child.rgt, parent.rgt)

	def test_validate_if_child_exists_on_trash(self):
		parent = self.create_location("_Test Parent To Delete", is_group=1)
		self.create_location("_Test Child Preventing Delete", parent_location=parent.name)

		with self.assertRaises(frappe.ValidationError):
			parent.delete()

	def test_location_area_aggregation(self):
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

	def test_on_doctype_update(self):
		on_doctype_update()

		result = frappe.db.sql(
			"""
				SHOW INDEX FROM `tabLocation`
				WHERE Column_name IN ('lft', 'rgt')
			""",
			as_dict=True,
		)

		indexes = {}

		for row in result:
			indexes.setdefault(row["Key_name"], []).append((row["Seq_in_index"], row["Column_name"]))

		self.assertIn([(1, "lft"), (2, "rgt")], [sorted(columns) for columns in indexes.values()])
		self.assertTrue(len(result) >= 2)
