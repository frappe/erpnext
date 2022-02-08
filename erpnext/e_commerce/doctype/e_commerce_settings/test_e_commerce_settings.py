# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import unittest

import frappe

from erpnext.e_commerce.doctype.e_commerce_settings.e_commerce_settings import (
	ShoppingCartSetupError,
)


class TestECommerceSettings(unittest.TestCase):
	def setUp(self):
		frappe.db.sql("""delete from `tabSingles` where doctype="Shipping Cart Settings" """)

	def get_cart_settings(self):
		return frappe.get_doc({"doctype": "E Commerce Settings",
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
	# 	self.assertRaises(ShoppingCartSetupError, cart_settings.validate_exchange_rates_exist)

	# 	from erpnext.setup.doctype.currency_exchange.test_currency_exchange import (
	# 		test_records as currency_exchange_records,
	# 	)
	# 	frappe.get_doc(currency_exchange_records[0]).insert()
	# 	cart_settings.validate_exchange_rates_exist()

	def test_tax_rule_validation(self):
		frappe.db.sql("update `tabTax Rule` set use_for_shopping_cart = 0")
		frappe.db.commit() # nosemgrep

		cart_settings = self.get_cart_settings()
		cart_settings.enabled = 1
		if not frappe.db.get_value("Tax Rule", {"use_for_shopping_cart": 1}, "name"):
			self.assertRaises(ShoppingCartSetupError, cart_settings.validate_tax_rule)

		frappe.db.sql("update `tabTax Rule` set use_for_shopping_cart = 1")

def setup_e_commerce_settings(values_dict):
	"Accepts a dict of values that updates E Commerce Settings."
	if not values_dict:
		return

	doc = frappe.get_doc("E Commerce Settings", "E Commerce Settings")
	doc.update(values_dict)
	doc.save()

test_dependencies = ["Tax Rule"]
