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

	def test_average_prices_use_current_list_prices_in_the_company_currency(self):
		variant = create_variant("_Test Variant Item", {"Test Size": "Small"})
		variant.insert(ignore_if_duplicate=True)
		frappe.get_doc(
			{"doctype": "Price List", "price_list_name": "_Test USD Selling", "currency": "USD", "selling": 1}
		).insert(ignore_if_duplicate=True)

		for price_list, rate, extra in (
			("Standard Selling", 100, {}),
			("Standard Selling", 8300, {"customer": "_Test Customer"}),
			("_Test USD Selling", 100, {}),
		):
			frappe.get_doc(
				{
					"doctype": "Item Price",
					"item_code": variant.name,
					"price_list": price_list,
					"price_list_rate": rate,
					**extra,
				}
			).insert()

		row = next(
			row
			for row in self.run_report(item="_Test Variant Item")
			if row.get("variant_name") == variant.name
		)

		self.assertEqual(row.get("avg_selling_price_list_rate"), 100)

	def test_current_stock_counts_only_permitted_warehouses(self):
		from frappe.permissions import add_user_permission

		variant = create_variant("_Test Variant Item", {"Test Size": "Small"})
		variant.insert(ignore_if_duplicate=True)
		for warehouse, qty in (("Stores - _TC", 18), ("Finished Goods - _TC", 7)):
			make_stock_entry(item_code=variant.name, to_warehouse=warehouse, qty=qty, rate=100)

		user = "variant-details-warehouse@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{"doctype": "User", "email": user, "first_name": "Variant Details", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.get_doc("User", user).add_roles("Stock Manager", "Sales User")
		add_user_permission("Warehouse", "Finished Goods - _TC", user)

		frappe.set_user(user)
		try:
			rows = self.run_report(item="_Test Variant Item")
		finally:
			frappe.set_user("Administrator")

		row = next(row for row in rows if row.get("variant_name") == variant.name)
		self.assertEqual(row.get("current_stock"), 7)
