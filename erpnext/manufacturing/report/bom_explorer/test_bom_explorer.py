# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest
from unittest.mock import patch

import frappe

from erpnext.manufacturing.report.bom_explorer.bom_explorer import get_exploded_items


class TestBOMExplorer(unittest.TestCase):
	def test_nested_bom_normalizes_and_accumulates_qty(self):
		def item(item_code, qty, stock_qty, bom_no="", uom="Nos", child_bom_qty=None):
			return frappe._dict(
				item_code=item_code,
				item_name=item_code,
				description="",
				qty=qty,
				stock_qty=stock_qty,
				bom_no=bom_no,
				child_bom_qty=child_bom_qty,
				uom=uom,
				idx=1,
				is_phantom_item=0,
			)

		children = {
			"root": [item("parent", 2, 20, "parent-bom", "Box", 5)],
			"parent-bom": [item("child", 3, 12, "child-bom", "Pack", 4)],
			"child-bom": [item("raw-material", 2, 2, uom="Kg")],
		}

		def get_items(_doctype, filters, **kwargs):
			self.assertIn("bom_no.quantity as child_bom_qty", kwargs["fields"])
			return children[filters["parent"]]

		data = []
		with patch.object(frappe, "get_all", side_effect=get_items):
			get_exploded_items("root", data)

		self.assertEqual([row["qty"] for row in data], [2, 12, 24])
