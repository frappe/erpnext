# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.selling.report.customer_wise_item_price.customer_wise_item_price import execute
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.tests.utils import ERPNextTestSuite

PRICE_LIST = "Standard Selling"


class TestCustomerWiseItemPrice(ERPNextTestSuite):
	"""The report lists sales items with the selling rate from the customer's price
	list and the available stock (summed across warehouses)."""

	def setUp(self):
		self.item = make_item(properties={"is_stock_item": 1, "is_sales_item": 1}).name
		self.customer = self.create_customer()
		frappe.get_doc(
			{
				"doctype": "Item Price",
				"item_code": self.item,
				"price_list": PRICE_LIST,
				"selling": 1,
				"price_list_rate": 250,
			}
		).insert()
		make_stock_entry(item_code=self.item, to_warehouse="Stores - _TC", qty=10, rate=100)

	def create_customer(self, name="_Test CWIP Customer", price_list=PRICE_LIST):
		if not frappe.db.exists("Customer", name):
			customer = frappe.new_doc("Customer")
			customer.customer_name = name
			customer.customer_group = "_Test Customer Group"
			customer.territory = "_Test Territory"
			customer.default_price_list = price_list
			customer.insert()
		return name

	def make_item_price(self, **values):
		price = frappe.new_doc("Item Price")
		price.update({"item_code": self.item, "price_list": PRICE_LIST, "selling": 1, **values})
		price.insert()

	def run_report(self, **extra):
		filters = frappe._dict({"customer": self.customer})
		filters.update(extra)
		return execute(filters)[1]

	def report_row(self, **extra):
		rows = self.run_report(item=self.item, **extra)
		return next((r for r in rows if r["item_code"] == self.item), None)

	def test_customer_filter_is_mandatory(self):
		self.assertRaises(frappe.ValidationError, execute, frappe._dict({}))

	def test_selling_rate_and_available_stock_for_item(self):
		rows = self.run_report(item=self.item)

		row = next((r for r in rows if r["item_code"] == self.item), None)
		self.assertIsNotNone(row, "Sales item missing from report")
		self.assertEqual(row["item_name"], frappe.db.get_value("Item", self.item, "item_name"))
		self.assertEqual(row["selling_rate"], 250)  # from the customer's price list
		self.assertEqual(row["available_stock"], 10)  # stocked into Stores - _TC
		self.assertEqual(row["price_list"], PRICE_LIST)

	def test_item_filter_scopes_to_single_item(self):
		other = make_item(properties={"is_stock_item": 1, "is_sales_item": 1}).name

		item_codes = {r["item_code"] for r in self.run_report(item=self.item)}
		self.assertIn(self.item, item_codes)
		self.assertNotIn(other, item_codes)

	def test_other_customers_special_price_is_not_shown(self):
		other = self.create_customer("_Test CWIP Other")
		self.make_item_price(customer=other, price_list_rate=700)

		row = self.report_row()
		self.assertEqual(row["selling_rate"], 250)  # the generic rate, not the other customer's 700

	def test_expired_and_other_uom_prices_are_ignored(self):
		self.make_item_price(
			customer=self.customer, price_list_rate=500, valid_from="2000-01-01", valid_upto="2000-12-31"
		)
		item = frappe.get_doc("Item", self.item)
		item.append("uoms", {"uom": "Box", "conversion_factor": 10})
		item.save()
		self.make_item_price(price_list_rate=999, uom="Box")

		row = self.report_row()
		self.assertEqual(row["selling_rate"], 250)  # current, stock-uom rate

	def test_falls_back_to_selling_settings_price_list(self):
		# customer's own list yields a zero rate -> must still fall back, as a transaction does
		zero_pl = "_Test CWIP Zero"
		if not frappe.db.exists("Price List", zero_pl):
			price_list = frappe.new_doc("Price List")
			price_list.price_list_name = zero_pl
			price_list.selling = 1
			price_list.insert()
		customer = self.create_customer("_Test CWIP Zero PL", price_list=zero_pl)
		self.make_item_price(price_list=zero_pl, price_list_rate=0)
		frappe.db.set_single_value(
			"Selling Settings", {"fallback_to_default_price_list": 1, "selling_price_list": PRICE_LIST}
		)

		row = self.report_row(customer=customer)
		self.assertEqual(row["selling_rate"], 250)  # the fallback list's rate, not the 0 on the customer list
		self.assertEqual(row["price_list"], PRICE_LIST)
