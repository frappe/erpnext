# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.controllers.item_variant import create_variant
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.item_variant_details.item_variant_details import execute


class TestItemVariantDetails(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def run_report(self, **extra):
		return execute(frappe._dict(extra))[1]

	def test_open_orders_leave_out_delivered_and_closed_orders(self):
		from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
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
