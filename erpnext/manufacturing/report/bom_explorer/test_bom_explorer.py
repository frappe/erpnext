# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest
from unittest.mock import patch

import frappe

from erpnext.manufacturing.report.bom_explorer.bom_explorer import get_exploded_items


class TestBOMExplorer(unittest.TestCase):
	def test_nested_bom_normalizes_and_accumulates_qty(self):
		def item(item_code, qty, stock_qty, bom_no="", uom="Nos"):
			return frappe._dict(
				item_code=item_code,
				item_name=item_code,
				description="",
				qty=qty,
				stock_qty=stock_qty,
				bom_no=bom_no,
				uom=uom,
				idx=1,
			)

		children = {
			"root": [item("parent", 2, 20, "parent-bom", "Box")],
			"parent-bom": [item("child", 3, 12, "child-bom", "Pack")],
			"child-bom": [item("raw-material", 2, 2, uom="Kg")],
		}
		bom_quantities = {"parent-bom": 5, "child-bom": 4}

		def get_items(_doctype, filters, **kwargs):
			return children[filters["parent"]]

		def get_bom_quantity(_doctype, name, _fieldname):
			return bom_quantities[name]

		data = []
		with (
			patch.object(frappe, "get_all", side_effect=get_items),
			patch.object(frappe, "get_cached_value", side_effect=get_bom_quantity),
		):
			get_exploded_items("root", data)

		self.assertEqual([row["qty"] for row in data], [2, 12, 24])
