# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import json
import os

import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.material_request.test_material_request import make_material_request
from erpnext.tests.utils import ERPNextTestSuite


class TestRequestedItemsToBeTransferred(ERPNextTestSuite):
	def run_query(self, request):
		path = os.path.join(os.path.dirname(__file__), "requested_items_to_be_transferred.json")
		query = json.load(open(path))["query"]
		return [row for row in frappe.db.sql(query) if row[0] == request]

	def test_pending_qty_is_in_the_stock_uom(self):
		item = make_item(
			properties={
				"is_stock_item": 1,
				"stock_uom": "Nos",
				"uoms": [{"uom": "Box", "conversion_factor": 12}],
			}
		).name
		request = make_material_request(
			item_code=item, qty=2, uom="Box", conversion_factor=12, material_request_type="Material Transfer"
		)
		frappe.db.set_value("Material Request Item", request.items[0].name, "ordered_qty", 3)

		rows = self.run_query(request.name)

		self.assertEqual([(row[3], row[4], row[6]) for row in rows], [(24, "Nos", 21)])
