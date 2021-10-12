# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals

import unittest

import frappe

from erpnext.shopping_cart.doctype.shopping_cart_settings.shopping_cart_settings import (
	ShoppingCartSetupError,
)


class TestShoppingCartSettings(unittest.TestCase):
	def setUp(self):
		frappe.db.sql("""delete from `tabSingles` where doctype="Shipping Cart Settings" """)

	def get_cart_settings(self):
		return frappe.get_doc({"doctype": "Shopping Cart Settings",
			"company": "_Test Company"})

	# NOTE: Exchangrate API has all enabled currencies that ERPNext supports.
	# We aren't checking just currency exchange record anymore
	# while validating price list currency exchange rate to that of company.
	# The API is being used to fetch the rate which again almost always
	# gives back a valid value (for valid currencies).
	# This makes the test obsolete.
	# Commenting because im not sure if there's a better test we can write

	# def test_exchange_rate_exists(self):
	# 	frappe.db.sql("""delete from `tabCurrency Exchange`""")

	# 	cart_settings = self.get_cart_settings()
	# 	cart_settings.price_list = "_Test Price List Rest of the World"
	# 	self.assertRaises(ShoppingCartSetupError, cart_settings.validate_price_list_exchange_rate)

	# 	from erpnext.setup.doctype.currency_exchange.test_currency_exchange import test_records as \
	# 		currency_exchange_records
	# 	frappe.get_doc(currency_exchange_records[0]).insert()
	# 	cart_settings.validate_price_list_exchange_rate()

	def test_tax_rule_validation(self):
		frappe.db.sql("update `tabTax Rule` set use_for_shopping_cart = 0")

		cart_settings = self.get_cart_settings()
		cart_settings.enabled = 1
		if not frappe.db.get_value("Tax Rule", {"use_for_shopping_cart": 1}, "name"):
			self.assertRaises(ShoppingCartSetupError, cart_settings.validate_tax_rule)

		frappe.db.sql("update `tabTax Rule` set use_for_shopping_cart = 1")

test_dependencies = ["Tax Rule"]
