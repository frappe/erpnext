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

	def make_report_user(self):
		user = "variant-details-warehouse@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{"doctype": "User", "email": user, "first_name": "Variant Details", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.get_doc("User", user).add_roles("Stock Manager", "Sales User")
		return user

	def get_current_stock_for_restricted_user(self, applicable_for=None):
		from frappe.permissions import add_user_permission

		variant = create_variant("_Test Variant Item", {"Test Size": "Small"})
		variant.insert(ignore_if_duplicate=True)
		for warehouse, qty in (("Stores - _TC", 18), ("Finished Goods - _TC", 7)):
			make_stock_entry(item_code=variant.name, to_warehouse=warehouse, qty=qty, rate=100)

		user = self.make_report_user()
		add_user_permission("Warehouse", "Finished Goods - _TC", user, applicable_for=applicable_for)

		frappe.set_user(user)
		try:
			rows = self.run_report(item="_Test Variant Item")
		finally:
			frappe.set_user("Administrator")

		return next(row for row in rows if row.get("variant_name") == variant.name).get("current_stock")

	def test_current_stock_counts_only_permitted_warehouses(self):
		self.assertEqual(self.get_current_stock_for_restricted_user(), 7)

	def test_permission_for_another_doctype_does_not_limit_current_stock(self):
		self.assertEqual(self.get_current_stock_for_restricted_user(applicable_for="Purchase Order"), 25)

	def test_average_prices_carry_their_currency(self):
		from erpnext.stock.report.item_variant_details.item_variant_details import get_report_currency

		variant = create_variant("_Test Variant Item", {"Test Size": "Small"})
		variant.insert(ignore_if_duplicate=True)
		columns, data = execute(frappe._dict(item="_Test Variant Item"))

		row = next(row for row in data if row.get("variant_name") == variant.name)
		price_columns = [column for column in columns if column["fieldname"].startswith("avg_")]
		self.assertEqual({column.get("options") for column in price_columns}, {"currency"})
		self.assertEqual(row.get("currency"), get_report_currency())

	def test_warehouse_filter_includes_descendants_of_group_warehouses(self):
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		group = frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": "_Test Variant Group",
				"is_group": 1,
				"company": "_Test Company",
			}
		).insert()
		child = frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": "_Test Variant Child",
				"parent_warehouse": group.name,
				"company": "_Test Company",
			}
		).insert()

		variant = create_variant("_Test Variant Item", {"Test Size": "Small"})
		variant.insert(ignore_if_duplicate=True)
		for warehouse, qty in (("Stores - _TC", 18), (child.name, 7)):
			make_stock_entry(item_code=variant.name, to_warehouse=warehouse, qty=qty, rate=100)
			make_sales_order(item_code=variant.name, qty=1, warehouse=warehouse)

		row = next(
			row
			for row in self.run_report(item="_Test Variant Item", warehouse=[group.name])
			if row.get("variant_name") == variant.name
		)

		self.assertEqual(row.get("current_stock"), 7)
		self.assertEqual(row.get("open_orders"), 1)

	def test_variants_grouped_under_their_templates(self):
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
		from erpnext.stock.doctype.item.test_item import make_item

		template = make_item(
			"_Test Variant Colour Item", {"has_variants": 1, "attributes": [{"attribute": "Test Colour"}]}
		).name
		create_variant("_Test Variant Item", {"Test Size": "Small"}).insert(ignore_if_duplicate=True)
		variants = []
		for colour, qty in (("Red", 4), ("Green", 6)):
			variant = create_variant(template, {"Test Colour": colour})
			variant.insert()
			make_stock_entry(item_code=variant.name, to_warehouse="Stores - _TC", qty=qty, rate=100)
			variants.append(variant.name)
		make_sales_order(
			item_list=[
				{"item_code": variant, "warehouse": "Stores - _TC", "qty": 1, "rate": 100}
				for variant in variants
			]
		)

		columns, data = execute(frappe._dict(item=["_Test Variant Item", template]))

		self.assertEqual(
			[row["variant_name"] for row in data if row["indent"] == 0], [template, "_Test Variant Item"]
		)
		self.assertTrue({"test_size", "test_colour"} <= {column["fieldname"] for column in columns})

		template_row = data[0]
		variant_rows = [row for row in data if row.get("template") == template]
		self.assertEqual(template_row["indent"], 0)
		self.assertEqual(template_row["current_stock"], 10)
		self.assertEqual(template_row["stock_uom"], frappe.db.get_value("Item", template, "stock_uom"))
		self.assertEqual(template_row["open_orders"], 1)
		self.assertEqual({row["variant_name"] for row in variant_rows}, set(variants))
		for row in variant_rows:
			self.assertEqual((row["indent"], row["template"], row["open_orders"]), (1, template, 1))

	def test_template_stock_left_blank_when_variant_uoms_differ(self):
		from erpnext.stock.doctype.item.test_item import make_item

		template = make_item(
			"_Test Variant Colour Item", {"has_variants": 1, "attributes": [{"attribute": "Test Colour"}]}
		)
		with self.change_settings("Item Variant Settings", {"allow_different_uom": 1}):
			create_variant(template.name, {"Test Colour": "Red"}).insert()
			green = create_variant(template.name, {"Test Colour": "Green"})
			green.stock_uom = "_Test UOM 1"
			green.insert()

		template_row, *variant_rows = self.run_report(item=[template.name])

		self.assertEqual(
			[template_row[field] for field in ("stock_uom", "current_stock", "in_production")], [None] * 3
		)
		self.assertEqual({row["stock_uom"] for row in variant_rows}, {template.stock_uom, "_Test UOM 1"})

	def test_item_group_filter_includes_templates_of_descendant_groups(self):
		from erpnext.stock.doctype.item.test_item import make_item

		parent = frappe.get_doc(
			{"doctype": "Item Group", "item_group_name": "_Test Variant Parent Group", "is_group": 1}
		).insert()
		child = frappe.get_doc(
			{
				"doctype": "Item Group",
				"item_group_name": "_Test Variant Child Group",
				"parent_item_group": parent.name,
			}
		).insert()
		template = make_item(
			"_Test Variant Colour Item",
			{"has_variants": 1, "item_group": child.name, "attributes": [{"attribute": "Test Colour"}]},
		).name
		variant = create_variant(template, {"Test Colour": "Red"}).insert()

		rows = self.run_report(item_group=[parent.name])

		self.assertEqual(
			[(row["variant_name"], row["item_group"]) for row in rows],
			[(template, child.name), (variant.name, child.name)],
		)

	def test_items_and_item_groups_filters_are_exclusive(self):
		self.assertEqual(self.run_report(), [])
		self.assertRaises(
			frappe.ValidationError, self.run_report, item=["_Test Variant Item"], item_group=["Products"]
		)

	def test_template_totals_leave_out_variants_hidden_by_user_permissions(self):
		from frappe.permissions import add_user_permission

		from erpnext.stock.doctype.item.test_item import make_item

		template = make_item(
			"_Test Variant Colour Item", {"has_variants": 1, "attributes": [{"attribute": "Test Colour"}]}
		).name
		variants = []
		for colour, qty in (("Red", 4), ("Green", 6)):
			variant = create_variant(template, {"Test Colour": colour}).insert()
			make_stock_entry(item_code=variant.name, to_warehouse="Stores - _TC", qty=qty, rate=100)
			variants.append(variant.name)

		user = self.make_report_user()
		for item in (template, variants[0]):
			add_user_permission("Item", item, user)

		with self.set_user(user):
			template_row, *variant_rows = self.run_report(item=[template])

		self.assertEqual(template_row["current_stock"], 4)
		self.assertEqual([row["variant_name"] for row in variant_rows], [variants[0]])

	def test_warehouse_filter_accepts_a_single_warehouse_string(self):
		variant = create_variant("_Test Variant Item", {"Test Size": "Small"})
		variant.insert(ignore_if_duplicate=True)
		for warehouse, qty in (("Stores - _TC", 18), ("Finished Goods - _TC", 7)):
			make_stock_entry(item_code=variant.name, to_warehouse=warehouse, qty=qty, rate=100)

		row = next(
			row
			for row in self.run_report(item="_Test Variant Item", warehouse="Finished Goods - _TC")
			if row.get("variant_name") == variant.name
		)

		self.assertEqual(row.get("current_stock"), 7)
