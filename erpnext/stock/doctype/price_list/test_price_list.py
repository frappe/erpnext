# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe.utils import random_string

from erpnext.tests.utils import ERPNextTestSuite


class TestPriceList(ERPNextTestSuite):
	def make_price_list(self, currency="INR", buying=1, selling=1):
		price_list = frappe.get_doc(
			{
				"doctype": "Price List",
				"price_list_name": "_Test PL " + random_string(10),
				"enabled": 1,
				"currency": currency,
				"buying": buying,
				"selling": selling,
			}
		).insert()
		return price_list

	def make_item_price(self, price_list, item_code="_Test Item", rate=100):
		return frappe.get_doc(
			{
				"doctype": "Item Price",
				"item_code": item_code,
				"price_list": price_list,
				"price_list_rate": rate,
			}
		).insert()

	def test_update_item_price_propagates_currency_and_flags(self):
		# Price List starts in INR, applicable for both buying and selling.
		price_list = self.make_price_list(currency="INR", buying=1, selling=1)

		ip1 = self.make_item_price(price_list.name, item_code="_Test Item", rate=100)
		ip2 = self.make_item_price(price_list.name, item_code="_Test Item 2", rate=250)

		# Sanity: Item Price rows inherited the Price List's initial state.
		for ip in (ip1, ip2):
			row = frappe.db.get_value("Item Price", ip.name, ["currency", "buying", "selling"], as_dict=True)
			self.assertEqual(row.currency, "INR")
			self.assertEqual(row.buying, 1)
			self.assertEqual(row.selling, 1)

		# Change the Price List's currency and flip the buying flag off.
		# on_update -> update_item_price() should bulk-UPDATE every Item Price
		# linked to this Price List.
		price_list.currency = "USD"
		price_list.buying = 0
		price_list.selling = 1
		price_list.save()

		for ip in (ip1, ip2):
			row = frappe.db.get_value("Item Price", ip.name, ["currency", "buying", "selling"], as_dict=True)
			self.assertEqual(row.currency, "USD")
			self.assertEqual(row.buying, 0)
			self.assertEqual(row.selling, 1)

	def test_update_item_price_scoped_to_own_price_list(self):
		# Two independent Price Lists; updating one must not touch the other's
		# Item Price rows (the WHERE price_list == self.name clause).
		pl_a = self.make_price_list(currency="INR", buying=1, selling=1)
		pl_b = self.make_price_list(currency="INR", buying=1, selling=1)

		ip_a = self.make_item_price(pl_a.name, item_code="_Test Item", rate=100)
		ip_b = self.make_item_price(pl_b.name, item_code="_Test Item", rate=100)

		pl_a.currency = "USD"
		pl_a.buying = 0
		pl_a.save()

		row_a = frappe.db.get_value("Item Price", ip_a.name, ["currency", "buying"], as_dict=True)
		self.assertEqual(row_a.currency, "USD")
		self.assertEqual(row_a.buying, 0)

		# pl_b was untouched, so its Item Price must keep the original values.
		row_b = frappe.db.get_value("Item Price", ip_b.name, ["currency", "buying"], as_dict=True)
		self.assertEqual(row_b.currency, "INR")
		self.assertEqual(row_b.buying, 1)
