# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals
import frappe
import unittest

from erpnext.e_commerce.doctype.e_commerce_settings.e_commerce_settings import ShoppingCartSetupError

class TestECommerceSettings(unittest.TestCase):
	def setUp(self):
		frappe.db.sql("""delete from `tabSingles` where doctype="Shipping Cart Settings" """)

	def get_cart_settings(self):
		return frappe.get_doc({"doctype": "E Commerce Settings",
			"company": "_Test Company"})

	def test_exchange_rate_exists(self):
		frappe.db.sql("""delete from `tabCurrency Exchange`""")

		cart_settings = self.get_cart_settings()
		cart_settings.price_list = "_Test Price List Rest of the World"
		self.assertRaises(ShoppingCartSetupError, cart_settings.validate_exchange_rates_exist)

		from erpnext.setup.doctype.currency_exchange.test_currency_exchange import test_records as \
			currency_exchange_records
		frappe.get_doc(currency_exchange_records[0]).insert()
		cart_settings.validate_exchange_rates_exist()

	def test_tax_rule_validation(self):
		frappe.db.sql("update `tabTax Rule` set use_for_shopping_cart = 0")
		frappe.db.commit()

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
