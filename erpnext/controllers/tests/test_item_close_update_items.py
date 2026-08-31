# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json

import frappe
from frappe.utils import add_days, nowdate

from erpnext.accounts.services.child_item_update import update_child_qty_rate
from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.controllers.item_close import update_closed_status
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.tests.utils import ERPNextTestSuite

WAREHOUSE = "_Test Warehouse - _TC"


class TestUpdateItemsWithClosedRows(ERPNextTestSuite):
	def setUp(self):
		self.first_item = make_item(properties={"is_stock_item": 1}).name
		self.second_item = make_item(properties={"is_stock_item": 1}).name

	def make_purchase_order(self):
		po = create_purchase_order(item_code=self.first_item, qty=10, rate=100, do_not_save=True)
		po.append(
			"items",
			{
				"item_code": self.second_item,
				"warehouse": WAREHOUSE,
				"qty": 10,
				"rate": 100,
				"schedule_date": add_days(nowdate(), 1),
			},
		)
		po.set_missing_values()
		po.insert()
		po.submit()
		update_closed_status("Purchase Order", po.name, [po.items[1].name], 1)
		po.reload()
		return po

	def as_payload(self, rows, **overrides):
		return json.dumps(
			[
				{
					"docname": row.name,
					"item_code": row.item_code,
					"qty": overrides.get(row.name, row.qty),
					"rate": row.rate,
					"uom": row.uom,
					"conversion_factor": row.conversion_factor,
					"description": row.description,
					"schedule_date": str(row.schedule_date),
				}
				for row in rows
			]
		)

	def test_payload_without_the_closed_row_does_not_delete_it(self):
		"""The dialog omits closed rows, and absence must not read as removal."""
		po = self.make_purchase_order()
		open_row, closed_row = po.items[0], po.items[1]

		update_child_qty_rate("Purchase Order", self.as_payload([open_row], **{open_row.name: 15}), po.name)

		po.reload()
		self.assertEqual(len(po.items), 2)
		self.assertEqual(po.items[0].qty, 15)
		self.assertTrue(po.items[1].closed)
		self.assertEqual(po.items[1].name, closed_row.name)

	def test_closed_row_cannot_be_changed_through_the_api(self):
		"""The dialog hides closed rows, but the whitelisted call is the real gate."""
		po = self.make_purchase_order()
		closed_row = po.items[1]

		self.assertRaises(
			frappe.ValidationError,
			update_child_qty_rate,
			"Purchase Order",
			self.as_payload(po.items, **{closed_row.name: 99}),
			po.name,
		)

		po.reload()
		self.assertEqual(po.items[1].qty, 10)

	def test_unchanged_closed_row_in_the_payload_is_tolerated(self):
		"""A caller sending the whole table untouched should not be rejected."""
		po = self.make_purchase_order()

		update_child_qty_rate("Purchase Order", self.as_payload(po.items), po.name)

		po.reload()
		self.assertEqual(len(po.items), 2)
		self.assertTrue(po.items[1].closed)
