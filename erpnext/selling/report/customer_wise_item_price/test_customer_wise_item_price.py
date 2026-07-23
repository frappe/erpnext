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

	def create_customer(self):
		name = "_Test CWIP Customer"
		if not frappe.db.exists("Customer", name):
			frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": name,
					"customer_group": "_Test Customer Group",
					"territory": "_Test Territory",
					"default_price_list": PRICE_LIST,
				}
			).insert()
		return name

	def run_report(self, **extra):
		filters = frappe._dict({"customer": self.customer})
		filters.update(extra)
		return execute(filters)[1]

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
