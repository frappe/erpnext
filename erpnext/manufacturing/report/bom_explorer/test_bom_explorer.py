# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.manufacturing.doctype.bom.test_bom import create_nested_bom
from erpnext.manufacturing.report.bom_explorer.bom_explorer import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestBOMExplorer(ERPNextTestSuite):
	def setUp(self):
		# the tests look up `_Test FG Item`'s BOM, which comes from the BOM fixtures;
		# load them so the file also passes when run in isolation
		self.load_test_records("BOM")

	def run_report(self, bom):
		filters = frappe._dict({"bom": bom})
		return execute(filters)[1]

	def top_level_rows_by_item(self, data):
		# key only the direct (indent 0) components, so an item that also appears in a
		# deeper sub-assembly can't overwrite the top-level row we assert against
		return {row["item_code"]: row for row in data if row["indent"] == 0}

	def test_default_bom_lists_components_at_top_level(self):
		bom = frappe.db.get_value("BOM", {"item": "_Test FG Item", "is_active": 1, "is_default": 1})
		self.assertIsNotNone(bom, "Default active BOM for _Test FG Item not found")

		data = self.run_report(bom)
		rows_by_item = self.top_level_rows_by_item(data)

		self.assertIn("_Test Item", rows_by_item)
		self.assertIn("_Test Item Home Desktop 100", rows_by_item)

		for item_code in ("_Test Item", "_Test Item Home Desktop 100"):
			row = rows_by_item[item_code]
			self.assertEqual(row["indent"], 0)
			self.assertEqual(row["bom_level"], 0)

	def test_qty_matches_bom_item_qty(self):
		bom = frappe.db.get_value("BOM", {"item": "_Test FG Item", "is_active": 1, "is_default": 1})
		data = self.run_report(bom)
		rows_by_item = self.top_level_rows_by_item(data)

		for bom_item in frappe.get_all(
			"BOM Item", filters={"parent": bom}, fields=["item_code", "qty", "uom"]
		):
			row = rows_by_item[bom_item.item_code]
			self.assertEqual(row["qty"], bom_item.qty)
			self.assertEqual(row["uom"], bom_item.uom)

	def test_nested_bom_shows_deeper_level(self):
		# Sub-assembly: "sub" is itself a BOM containing "leaf".
		parent_bom = create_nested_bom(
			{"parent": {"sub": {"leaf": {}}, "flat": {}}},
			prefix="_Test explorer ",
		)

		data = self.run_report(parent_bom.name)
		rows_by_item = {row["item_code"]: row for row in data}

		sub_item = "_Test explorer sub"
		leaf_item = "_Test explorer leaf"
		flat_item = "_Test explorer flat"

		self.assertIn(sub_item, rows_by_item)
		self.assertIn(flat_item, rows_by_item)
		self.assertIn(leaf_item, rows_by_item)

		# Direct components of the parent sit at level 0.
		self.assertEqual(rows_by_item[flat_item]["indent"], 0)
		self.assertEqual(rows_by_item[sub_item]["indent"], 0)

		# The sub-assembly row carries its own BOM reference.
		self.assertTrue(rows_by_item[sub_item]["bom"])

		# The leaf belongs to the sub-assembly, so it is exploded one level deeper.
		self.assertEqual(rows_by_item[leaf_item]["indent"], 1)
		self.assertEqual(rows_by_item[leaf_item]["bom_level"], 1)
