# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.selling.doctype.customer.test_customer import create_internal_customer
from erpnext.selling.doctype.quotation.test_quotation import make_quotation
from erpnext.selling.doctype.sales_order.mapper import make_delivery_note
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.tests.permission_test_utils import make_fenced_user
from erpnext.tests.utils import ERPNextTestSuite


class TestSellingControllerConversions(ERPNextTestSuite):
	def test_gross_profit_uses_company_currency(self):
		self.load_test_records("Sales Order")
		self.load_test_records("Quotation")
		item = make_item(
			properties={"is_stock_item": 1, "stock_uom": "Nos"},
			uoms=[{"uom": "Box", "conversion_factor": 5}],
		)
		make_stock_entry(item_code=item.name, target="_Test Warehouse - _TC", qty=50, basic_rate=5200)

		for make_document in (make_sales_order, make_quotation):
			for currency, conversion_rate, rate in (("INR", 1, 8300), ("USD", 83, 100)):
				for uom, conversion_factor in (("Nos", 1), ("Box", 5)):
					with self.subTest(doctype=make_document.__name__, currency=currency, uom=uom):
						doc = make_document(
							item_code=item.name,
							qty=2,
							rate=rate * conversion_factor,
							uom=uom,
							currency=currency,
							do_not_save=True,
						)
						doc.conversion_rate = conversion_rate
						doc.insert().submit()
						doc.reload()
						self.assertEqual(doc.docstatus, 1)
						self.assertEqual(doc.items[0].base_net_rate, 8300 * conversion_factor)
						self.assertEqual(doc.items[0].valuation_rate, 5200)
						self.assertEqual(doc.items[0].stock_qty, 2 * conversion_factor)
						self.assertEqual(doc.items[0].gross_profit, 6200 * conversion_factor)

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
		make_stock_entry(item_code="_Test Item", target="_Test Warehouse - _TC", qty=20, basic_rate=100)

		so = make_sales_order(qty=10)

		dn = make_delivery_note(so.name)
		dn.items[0].qty = 4
		dn.insert()
		dn.submit()

		so.reload()
		self.assertEqual(so.per_delivered, 40.0)

	@ERPNextTestSuite.change_settings("Selling Settings", {"validate_selling_price": 1})
	def test_internal_transfer_skips_the_last_purchase_rate_check(self):
		"""An internal transfer moves stock at its valuation rate, below the last purchase rate."""
		item_code = make_item(properties={"is_stock_item": 1}).name
		make_stock_entry(item_code=item_code, target="Stores - TCP1", qty=10, basic_rate=89.48)
		frappe.db.set_value("Item", item_code, "last_purchase_rate", 120)

		dn = create_delivery_note(
			item_code=item_code,
			company="_Test Company with perpetual inventory",
			customer="_Test Internal Customer 2",
			cost_center="Main - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			qty=1,
			warehouse="Stores - TCP1",
			target_warehouse="Goods In Transit - TCP1",
		)

		self.assertEqual(dn.docstatus, 1)

	@ERPNextTestSuite.change_settings("Selling Settings", {"validate_selling_price": 1})
	def test_inter_company_sale_keeps_the_last_purchase_rate_check(self):
		item_code = make_item(properties={"is_stock_item": 0}).name
		frappe.db.set_value("Item", item_code, "last_purchase_rate", 120)
		customer = create_internal_customer(
			customer_name="_Test Internal Customer",
			represents_company="_Test Company 1",
			allowed_to_interact_with="Wind Power LLC",
		)

		si = create_sales_invoice(
			item_code=item_code,
			company="Wind Power LLC",
			customer=customer,
			debit_to="Debtors - WP",
			income_account="Sales - WP",
			expense_account="Cost of Goods Sold - WP",
			cost_center="Main - WP",
			currency="USD",
			rate=90,
			do_not_save=True,
		)

		self.assertRaisesRegex(frappe.ValidationError, "last purchase rate", si.save)
