# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.tests.permission_test_utils import make_fenced_user
from erpnext.tests.utils import ERPNextTestSuite


class TestSellingControllerConversions(ERPNextTestSuite):
	def test_maximum_discount_for_percentage_amount_and_rate(self):
		item = make_item(properties={"is_stock_item": 0, "max_discount": 10})
		item_price = frappe.get_doc(
			{
				"doctype": "Item Price",
				"item_code": item.name,
				"price_list": "Standard Selling",
				"price_list_rate": 100,
			}
		).insert()
		user = make_fenced_user("max-discount@example.com", ["Sales User"])

		with self.set_user(user):
			for values in (
				{"discount_percentage": 50},
				{"discount_amount": 50},
				{"rate": 50},
				{"margin_type": "Percentage", "margin_rate_or_amount": 25, "discount_amount": 25},
			):
				with self.subTest(values=values):
					order = make_sales_order(
						item_list=[{"item_code": item.name, "qty": 1, **values}],
						selling_price_list="Standard Selling",
						do_not_save=True,
					)
					with self.assertRaisesRegex(frappe.ValidationError, "Maximum discount for Item"):
						order.insert().submit()

			for values, expected_rate in (
				({"discount_percentage": 10}, 90),
				({"discount_amount": 10}, 90),
				({"rate": 90}, 90),
				({"margin_type": "Percentage", "margin_rate_or_amount": 25, "discount_amount": 12.5}, 112.5),
			):
				with self.subTest(values=values):
					order = make_sales_order(
						item_list=[{"item_code": item.name, "qty": 1, **values}],
						selling_price_list="Standard Selling",
					)
					self.assertEqual(order.docstatus, 1)
					self.assertEqual(order.items[0].price_list_rate, 100)
					self.assertEqual(order.items[0].rate, expected_rate)

		item_price.price_list_rate = 0.06
		item_price.save()
		with self.set_user(user):
			order = make_sales_order(
				item_list=[{"item_code": item.name, "qty": 1, "discount_percentage": 10}],
				selling_price_list="Standard Selling",
			)
			self.assertEqual(order.items[0].discount_amount, 0.01)
			self.assertEqual(order.items[0].rate, 0.05)

		for price_list_rate, rate in ((0, 50), (-100, -100)):
			item_price.price_list_rate = price_list_rate
			item_price.save()
			with (
				self.subTest(price_list_rate=price_list_rate),
				self.change_settings("Selling Settings", {"allow_negative_rates_for_items": 1}),
				self.set_user(user),
			):
				order = make_sales_order(
					item_list=[{"item_code": item.name, "qty": 1, "rate": rate}],
					selling_price_list="Standard Selling",
				)
				self.assertEqual(order.items[0].rate, rate)
				self.assertEqual(order.items[0].discount_amount, 0)

	def test_partial_delivery_updates_sales_order_status(self):
		# Submitting a Delivery Note against a Sales Order calls
		# SellingController.get_already_delivered_qty / get_so_qty_and_warehouse and StatusUpdater
		# (per_delivered via coalesce(sum(...))) -- all converted to query builder / ORM here.
		from erpnext.selling.doctype.sales_order.mapper import make_delivery_note
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		make_stock_entry(item_code="_Test Item", target="_Test Warehouse - _TC", qty=20, basic_rate=100)

		so = make_sales_order(qty=10)

		dn = make_delivery_note(so.name)
		dn.items[0].qty = 4
		dn.insert()
		dn.submit()

		so.reload()
		self.assertEqual(so.per_delivered, 40.0)
