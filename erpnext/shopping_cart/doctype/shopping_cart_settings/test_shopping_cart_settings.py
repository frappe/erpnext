# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import unittest
from erpnext.shopping_cart.doctype.shopping_cart_settings.shopping_cart_settings import ShoppingCartSetupError

class TestShoppingCartSettings(unittest.TestCase):
	def setUp(self):
		frappe.db.sql("""delete from `tabSingles` where doctype="Shipping Cart Settings" """)
		frappe.db.sql("""delete from `tabShopping Cart Price List`""")
		frappe.db.sql("""delete from `tabShopping Cart Taxes and Charges Master`""")
		frappe.db.sql("""delete from `tabShopping Cart Shipping Rule`""")
		
	def get_cart_settings(self):
		return frappe.get_doc({"doctype": "Shopping Cart Settings",
			"company": "_Test Company"})
		
	def test_price_list_territory_overlap(self):
		cart_settings = self.get_cart_settings()
		
		def _add_price_list(price_list):
			cart_settings.append("price_lists", {
				"doctype": "Shopping Cart Price List",
				"selling_price_list": price_list
			})
		
		for price_list in ("_Test Price List Rest of the World", "_Test Price List India",
			"_Test Price List"):
			_add_price_list(price_list)
		
		controller = cart_settings
		controller.validate_overlapping_territories("price_lists", "selling_price_list")
		
		_add_price_list("_Test Price List 2")
		
		controller = cart_settings
		self.assertRaises(ShoppingCartSetupError, controller.validate_overlapping_territories,
			"price_lists", "selling_price_list")
			
		return cart_settings
		
	def test_taxes_territory_overlap(self):
		cart_settings = self.get_cart_settings()
		
		def _add_tax_master(tax_master):
			cart_settings.append("sales_taxes_and_charges_masters", {
				"doctype": "Shopping Cart Taxes and Charges Master",
				"sales_taxes_and_charges_master": tax_master
			})
		
		for tax_master in ("_Test Sales Taxes and Charges Master", "_Test India Tax Master"):
			_add_tax_master(tax_master)
			
		controller = cart_settings
		controller.validate_overlapping_territories("sales_taxes_and_charges_masters",
			"sales_taxes_and_charges_master")
			
		_add_tax_master("_Test Sales Taxes and Charges Master - Rest of the World")
		
		controller = cart_settings
		self.assertRaises(ShoppingCartSetupError, controller.validate_overlapping_territories,
			"sales_taxes_and_charges_masters", "sales_taxes_and_charges_master")
		
	def test_exchange_rate_exists(self):
		frappe.db.sql("""delete from `tabCurrency Exchange`""")
		
		cart_settings = self.test_price_list_territory_overlap()
		controller = cart_settings
		self.assertRaises(ShoppingCartSetupError, controller.validate_exchange_rates_exist)
		
		from erpnext.setup.doctype.currency_exchange.test_currency_exchange import test_records as \
			currency_exchange_records
		frappe.get_doc(currency_exchange_records[0]).insert()
		controller.validate_exchange_rates_exist()
		
