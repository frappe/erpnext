# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.controllers.item_variant import create_variant
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.item_variant_details.item_variant_details import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestItemVariantDetails(ERPNextTestSuite):
	def run_report(self, **extra):
		return execute(frappe._dict(extra))[1]

	def test_variants_listed_for_template(self):
		template = "_Test Variant Item"

		variant = create_variant(template, {"Test Size": "Small"})
		variant.insert(ignore_if_duplicate=True)

		make_stock_entry(
			item_code=variant.name,
			to_warehouse="Stores - _TC",
			qty=5,
			rate=100,
		)

		rows = self.run_report(item=template)

		variant_rows = [row for row in rows if row.get("variant_name") == variant.name]
		self.assertEqual(len(variant_rows), 1)

		row = variant_rows[0]
		self.assertEqual(row.get("test_size"), "Small")
		self.assertEqual(row.get("current_stock"), 5)
		self.assertEqual(row.get("open_orders"), 0)

	def test_open_orders_leave_out_delivered_and_closed_orders(self):
		from erpnext.selling.doctype.sales_order.mapper import make_delivery_note
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		variant = create_variant("_Test Variant Item", {"Test Size": "Small"})
		variant.insert(ignore_if_duplicate=True)
		make_stock_entry(item_code=variant.name, to_warehouse="Stores - _TC", qty=10, rate=100)

		orders = [
			make_sales_order(item_code=variant.name, qty=2, warehouse="Stores - _TC") for _order in range(3)
		]
		make_delivery_note(orders[1].name).submit()
		orders[2].update_status("Closed")

		row = next(
			row
			for row in self.run_report(item="_Test Variant Item")
			if row.get("variant_name") == variant.name
		)

		self.assertEqual(row.get("open_orders"), 1)
