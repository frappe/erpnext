# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from unittest.mock import patch

import frappe
from frappe.utils import add_months, flt, today

from erpnext import get_company_currency
from erpnext.controllers.queries import get_blanket_orders
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.get_item_details import get_blanket_order_details
from erpnext.tests.utils import ERPNextTestSuite

from . import blanket_order_pricing
from .blanket_order import apply_price_list, make_order


class TestBlanketOrder(ERPNextTestSuite):
	def setUp(self):
		frappe.flags.args = frappe._dict()

	def test_sales_order_creation(self):
		bo = make_blanket_order(blanket_order_type="Selling")

		frappe.flags.args.doctype = "Sales Order"
		so = make_order(bo.name)
		so.currency = get_company_currency(so.company)
		so.delivery_date = today()
		so.items[0].qty = 10
		so.submit()

		self.assertEqual(so.doctype, "Sales Order")
		self.assertEqual(len(so.get("items")), len(bo.get("items")))

		# check the rate, quantity and updation for the ordered quantity
		self.assertEqual(so.items[0].rate, bo.items[0].rate)

		bo = frappe.get_doc("Blanket Order", bo.name)
		self.assertEqual(so.items[0].qty, bo.items[0].ordered_qty)

		# test the quantity
		frappe.flags.args.doctype = "Sales Order"
		so1 = make_order(bo.name)
		so1.currency = get_company_currency(so1.company)
		self.assertEqual(so1.items[0].qty, (bo.items[0].qty - bo.items[0].ordered_qty))

	def test_purchase_order_creation(self):
		bo = make_blanket_order(blanket_order_type="Purchasing")

		frappe.flags.args.doctype = "Purchase Order"
		po = make_order(bo.name)
		po.currency = get_company_currency(po.company)
		po.schedule_date = today()
		po.items[0].qty = 10
		po.submit()

		self.assertEqual(po.doctype, "Purchase Order")
		self.assertEqual(len(po.get("items")), len(bo.get("items")))

		# check the rate, quantity and updation for the ordered quantity
		self.assertEqual(po.items[0].rate, po.items[0].rate)

		bo = frappe.get_doc("Blanket Order", bo.name)
		self.assertEqual(po.items[0].qty, bo.items[0].ordered_qty)

		# test the quantity
		frappe.flags.args.doctype = "Purchase Order"
		po1 = make_order(bo.name)
		po1.currency = get_company_currency(po1.company)
		self.assertEqual(po1.items[0].qty, (bo.items[0].qty - bo.items[0].ordered_qty))

	def test_blanket_order_allowance(self):
		# Sales Order
		bo = make_blanket_order(blanket_order_type="Selling", quantity=100)

		frappe.flags.args.doctype = "Sales Order"
		so = make_order(bo.name)
		so.currency = get_company_currency(so.company)
		so.delivery_date = today()
		so.items[0].qty = 110
		self.assertRaises(frappe.ValidationError, so.submit)

		frappe.db.set_single_value("Selling Settings", "blanket_order_allowance", 10)
		so.submit()

		# Purchase Order
		bo = make_blanket_order(blanket_order_type="Purchasing", quantity=100)

		frappe.flags.args.doctype = "Purchase Order"
		po = make_order(bo.name)
		po.currency = get_company_currency(po.company)
		po.schedule_date = today()
		po.items[0].qty = 110
		self.assertRaises(frappe.ValidationError, po.submit)

		frappe.db.set_single_value("Buying Settings", "blanket_order_allowance", 10)
		po.submit()

	@ERPNextTestSuite.change_settings("Selling Settings", {"blanket_order_allowance": 0})
	@ERPNextTestSuite.change_settings("Buying Settings", {"blanket_order_allowance": 0})
	@ERPNextTestSuite.change_settings(
		"Stock Settings",
		{"over_delivery_receipt_allowance": 10, "role_allowed_to_over_deliver_receive": "Stock Manager"},
	)
	def test_stock_over_delivery_role_does_not_bypass_blanket_order_allowance(self):
		test_user = frappe.get_doc("User", "test@example.com")
		test_user.add_roles("Stock Manager")

		frappe.clear_cache()
		for blanket_order_type, doctype, date_field in (
			("Selling", "Sales Order", "delivery_date"),
			("Purchasing", "Purchase Order", "schedule_date"),
		):
			bo = make_blanket_order(blanket_order_type=blanket_order_type, quantity=100)
			frappe.flags.args.doctype = doctype
			order = make_order(bo.name)
			order.currency = get_company_currency(order.company)
			setattr(order, date_field, today())
			order.items[0].qty = 110

			with self.set_user("test@example.com"):
				order.flags.ignore_permissions = True
				self.assertRaises(frappe.ValidationError, order.submit)

	def test_party_item_code(self):
		item_doc = make_item("_Test Item 1 for Blanket Order")
		item_code = item_doc.name

		customer = "_Test Customer"
		supplier = "_Test Supplier"

		if not frappe.db.exists("Item Customer Detail", {"customer_name": customer, "parent": item_code}):
			item_doc.append("customer_items", {"customer_name": customer, "ref_code": "CUST-REF-1"})
			item_doc.save()

		if not frappe.db.exists("Item Supplier", {"supplier": supplier, "parent": item_code}):
			item_doc.append("supplier_items", {"supplier": supplier, "supplier_part_no": "SUPP-PART-1"})
			item_doc.save()

		# Blanket Order for Selling
		bo = make_blanket_order(blanket_order_type="Selling", customer=customer, item_code=item_code)
		self.assertEqual(bo.items[0].party_item_code, "CUST-REF-1")

		bo = make_blanket_order(blanket_order_type="Purchasing", supplier=supplier, item_code=item_code)
		self.assertEqual(bo.items[0].party_item_code, "SUPP-PART-1")

	def test_blanket_order_zero_quantity(self):
		bo = frappe.new_doc("Blanket Order")
		bo.blanket_order_type = "Selling"
		bo.company = "_Test Company"
		bo.customer = "_Test Customer"
		bo.from_date = today()
		bo.to_date = add_months(today(), 12)

		bo.append(
			"items",
			{
				"item_code": "_Test Item",
				"qty": 0,
				"rate": 100,
			},
		)

		with self.assertRaises(frappe.ValidationError):
			bo.insert()

	def test_multicurrency_blanket_order(self):
		company_currency = get_company_currency("_Test Company")
		transaction_currency = "USD" if company_currency != "USD" else "EUR"
		conversion_rate = 80
		rate = 5

		for blanket_order_type, target_doctypes in (
			("Selling", ("Sales Order", "Quotation")),
			("Purchasing", ("Purchase Order",)),
		):
			blanket_order = make_blanket_order(
				blanket_order_type=blanket_order_type,
				currency=transaction_currency,
				conversion_rate=conversion_rate,
				rate=rate,
			)

			self.assertEqual(blanket_order.currency, transaction_currency)
			self.assertEqual(blanket_order.conversion_rate, conversion_rate)
			self.assertEqual(blanket_order.items[0].base_rate, rate * conversion_rate)

			for target_doctype in target_doctypes:
				with self.subTest(target_doctype=target_doctype):
					frappe.flags.args.doctype = target_doctype
					target = make_order(blanket_order.name)

					self.assertEqual(target.currency, transaction_currency)
					self.assertEqual(target.conversion_rate, conversion_rate)
					self.assertEqual(target.items[0].rate, rate)
					self.assertEqual(target.items[0].base_rate, rate * conversion_rate)
					self.assertEqual(target.items[0].blanket_order_rate, rate)
					self.assertEqual(target.items[0].blanket_order, blanket_order.name)

	def test_price_list_rates_and_mapping(self):
		company = "_Test Company"
		company_currency = get_company_currency(company)
		transaction_currency = "USD" if company_currency != "USD" else "EUR"
		conversion_rate = 80
		price_list_rate = 800

		for blanket_order_type, price_list_field, target_doctypes in (
			("Selling", "selling_price_list", ("Sales Order", "Quotation")),
			("Purchasing", "buying_price_list", ("Purchase Order",)),
		):
			blanket_order, price_list = make_priced_blanket_order(
				blanket_order_type=blanket_order_type,
				company=company,
				currency=transaction_currency,
				conversion_rate=conversion_rate,
				price_list_rate=price_list_rate,
				qty=1000,
			)
			blanket_order.insert()
			blanket_order.submit()

			expected_rate = price_list_rate / conversion_rate
			self.assertEqual(blanket_order.price_list_currency, company_currency)
			self.assertEqual(blanket_order.plc_conversion_rate, 1)
			self.assertEqual(blanket_order.items[0].price_list_rate, expected_rate)
			self.assertEqual(blanket_order.items[0].base_price_list_rate, price_list_rate)
			self.assertEqual(blanket_order.items[0].rate, expected_rate)
			self.assertEqual(blanket_order.items[0].base_rate, price_list_rate)

			for target_doctype in target_doctypes:
				with self.subTest(target_doctype=target_doctype):
					frappe.flags.args.doctype = target_doctype
					target = make_order(blanket_order.name)

					self.assertEqual(target.get(price_list_field), price_list)
					self.assertEqual(target.price_list_currency, company_currency)
					self.assertEqual(target.plc_conversion_rate, 1)
					self.assertEqual(target.items[0].price_list_rate, expected_rate)
					self.assertEqual(target.items[0].base_price_list_rate, price_list_rate)
					self.assertEqual(target.items[0].rate, expected_rate)
					self.assertEqual(target.items[0].blanket_order, blanket_order.name)

	def test_applying_price_list_ignores_empty_item_rows(self):
		blanket_order = frappe.new_doc("Blanket Order")
		blanket_order.blanket_order_type = "Selling"
		blanket_order.company = "_Test Company"
		blanket_order.customer = "_Test Customer"
		blanket_order.from_date = today()
		blanket_order.append("items", {})

		pricing = apply_price_list(blanket_order.as_dict())

		self.assertEqual(pricing["children"], [])

	def test_price_list_rate_is_fetched_on_item_selection(self):
		company = "_Test Company"
		company_currency = get_company_currency(company)
		price_list_rate = 800
		blanket_order, _price_list = make_priced_blanket_order(
			company=company,
			currency=company_currency,
			conversion_rate=1,
			price_list_rate=price_list_rate,
			qty=0,
		)
		item = blanket_order.items[0]

		self.assertEqual(item.price_list_rate, price_list_rate)
		self.assertEqual(item.rate, price_list_rate)

	def test_price_list_conversion_uses_currency_precision(self):
		company = "_Test Company"
		company_currency = get_company_currency(company)
		transaction_currency = "USD" if company_currency != "USD" else "EUR"
		conversion_rate = 95.47
		price_list_rate = 100
		blanket_order, _price_list = make_priced_blanket_order(
			company=company,
			currency=transaction_currency,
			conversion_rate=conversion_rate,
			price_list_rate=price_list_rate,
		)
		item = blanket_order.items[0]
		expected_rate = flt(price_list_rate / conversion_rate, item.precision("rate"))
		expected_base_rate = flt(expected_rate * conversion_rate, item.precision("base_rate"))

		self.assertFalse(frappe.get_meta("Blanket Order Item").get_field("rate").precision)
		self.assertEqual(item.price_list_rate, expected_rate)
		self.assertEqual(item.base_price_list_rate, expected_base_rate)
		self.assertEqual(item.rate, expected_rate)
		self.assertEqual(item.base_rate, expected_base_rate)

		blanket_order.insert()
		blanket_order.submit()

		frappe.flags.args.doctype = "Sales Order"
		sales_order = make_order(blanket_order.name)
		sales_order.delivery_date = today()
		sales_order.insert()

		self.assertEqual(sales_order.items[0].price_list_rate, item.price_list_rate)
		self.assertEqual(sales_order.items[0].base_price_list_rate, item.base_price_list_rate)
		self.assertEqual(sales_order.items[0].rate, item.rate)
		self.assertEqual(sales_order.items[0].base_rate, item.base_rate)

	def test_applying_price_list_can_reset_conversion_rate(self):
		company_currency = get_company_currency("_Test Company")
		transaction_currency = "USD" if company_currency != "USD" else "EUR"
		blanket_order, _price_list = make_priced_blanket_order(
			currency=transaction_currency,
			conversion_rate=80,
			price_list_rate=100,
		)

		with patch(
			"erpnext.manufacturing.doctype.blanket_order.blanket_order_pricing.get_exchange_rate",
			return_value=95.47,
		):
			pricing = apply_price_list(blanket_order.as_dict(), reset_conversion_rate=True)

		self.assertEqual(pricing["parent"]["conversion_rate"], 95.47)
		expected_rate = flt(
			100 / pricing["parent"]["conversion_rate"],
			blanket_order.items[0].precision("rate"),
		)
		expected_base_rate = flt(
			expected_rate * pricing["parent"]["conversion_rate"],
			blanket_order.items[0].precision("base_rate"),
		)
		self.assertEqual(pricing["children"][0]["base_rate"], expected_base_rate)

	def test_blanket_order_lookup_filters_currency(self):
		company_currency = get_company_currency("_Test Company")
		transaction_currency = "USD" if company_currency != "USD" else "EUR"
		blanket_order = make_blanket_order(
			blanket_order_type="Selling",
			currency=transaction_currency,
			conversion_rate=80,
		)

		filters = {
			"company": blanket_order.company,
			"currency": transaction_currency,
			"blanket_order_type": "Selling",
			"item": blanket_order.items[0].item_code,
		}
		matching_orders = get_blanket_orders("Blanket Order", "", "name", 0, 20, filters)
		self.assertIn(blanket_order.name, [order[0] for order in matching_orders])

		filters["currency"] = company_currency
		other_currency_orders = get_blanket_orders("Blanket Order", "", "name", 0, 20, filters)
		self.assertNotIn(blanket_order.name, [order[0] for order in other_currency_orders])

		details = get_blanket_order_details(
			{
				"blanket_order": blanket_order.name,
				"company": blanket_order.company,
				"currency": company_currency,
				"customer": blanket_order.customer,
				"doctype": "Sales Order",
				"item_code": blanket_order.items[0].item_code,
				"transaction_date": today(),
			}
		)
		self.assertFalse(details)


def make_blanket_order(**args):
	args = frappe._dict(args)
	bo = new_blanket_order(
		blanket_order_type=args.blanket_order_type,
		company=args.company or "_Test Company",
		currency=args.currency,
		conversion_rate=args.conversion_rate or 1,
		customer=args.customer,
		supplier=args.supplier,
	)
	bo.append(
		"items",
		{
			"item_code": args.item_code or "_Test Item",
			"qty": args.quantity or 1000,
			"rate": args.rate or 100,
		},
	)

	bo.insert()
	bo.submit()
	return bo


def make_priced_blanket_order(
	blanket_order_type="Selling",
	company="_Test Company",
	currency=None,
	conversion_rate=1,
	price_list_rate=800,
	qty=1,
):
	price_list = make_blanket_order_price_list(get_company_currency(company), price_list_rate)
	blanket_order = new_blanket_order(
		blanket_order_type=blanket_order_type,
		company=company,
		currency=currency,
		conversion_rate=conversion_rate,
	)
	config = blanket_order_pricing.get_order_type_config(blanket_order_type)
	blanket_order.set(config["price_list_field"], price_list)
	item = blanket_order.append("items", {"item_code": "_Test Item", "qty": qty, "rate": 0})
	pricing = apply_price_list(blanket_order.as_dict())
	blanket_order.update(pricing["parent"])
	item.update({key: value for key, value in pricing["children"][0].items() if key != "name"})

	return blanket_order, price_list


def new_blanket_order(
	blanket_order_type,
	company="_Test Company",
	currency=None,
	conversion_rate=1,
	customer=None,
	supplier=None,
):
	blanket_order = frappe.new_doc("Blanket Order")
	blanket_order.blanket_order_type = blanket_order_type
	blanket_order.company = company
	blanket_order.currency = currency or get_company_currency(company)
	blanket_order.conversion_rate = conversion_rate
	blanket_order.from_date = today()
	blanket_order.to_date = add_months(blanket_order.from_date, months=12)

	config = blanket_order_pricing.get_order_type_config(blanket_order_type)
	party = customer if config["party_field"] == "customer" else supplier
	blanket_order.set(config["party_field"], party or f"_Test {config['party_type']}")

	return blanket_order


def make_blanket_order_price_list(currency, price_list_rate):
	price_list = "_Test Blanket Order Price List"
	if not frappe.db.exists("Price List", price_list):
		frappe.get_doc(
			{
				"doctype": "Price List",
				"price_list_name": price_list,
				"currency": currency,
				"selling": 1,
				"buying": 1,
			}
		).insert()
	else:
		frappe.db.set_value("Price List", price_list, {"currency": currency, "selling": 1, "buying": 1})

	item_price = frappe.db.get_value(
		"Item Price", {"price_list": price_list, "item_code": "_Test Item"}, "name"
	)
	if item_price:
		frappe.db.set_value("Item Price", item_price, "price_list_rate", price_list_rate)
	else:
		frappe.get_doc(
			{
				"doctype": "Item Price",
				"price_list": price_list,
				"item_code": "_Test Item",
				"price_list_rate": price_list_rate,
			}
		).insert()

	return price_list
