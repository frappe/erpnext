# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import unittest
from erpnext.shopping_cart.test_cart import _name, _make_price_list, _make_tax_template, make_items
from erpnext.shopping_cart.doctype.shopping_cart_settings.shopping_cart_settings import MissingCurrencyExchangeError

class TestShoppingCartSettings(unittest.TestCase):
	def setUp(self):
		frappe.db.sql("""delete from `tabSingles` where doctype="Shipping Cart Settings" """)
		frappe.db.sql("""delete from `tabShopping Cart Country`""")
		frappe.db.sql("""delete from `tabShopping Cart Price List`""")
		frappe.db.sql("""delete from `tabShopping Cart Taxes and Charges Master`""")
		frappe.db.sql("""delete from `tabShopping Cart Shipping Rule`""")
		# and now my record is clean :P

	def get_shopping_cart_settings(self):
		return frappe.get_doc({
			"doctype": "Shopping Cart Settings",
			"company": "_Test Company",
			"default_territory": "Rest of the World",
			"default_customer_group": "_Test Customer Group",
			"quotation_series": "_T-Cart-"
		})

	def test_price_list_overlap(self):
		make_items()

		# example: _Test Cart Price List INR
		_make_price_list(_name("Price List", "INR"), "INR", 1, {"if_address_matches": "Home Country"})
		_make_price_list(_name("Price List", "USD"), "USD", 60, {"if_address_matches": "Rest of the World"})
		_make_price_list(_name("Price List", "EUR"), "EUR", 70, {"if_address_matches": "Rest of the World"})

		settings = self.get_shopping_cart_settings()
		settings.set("price_lists", [
			{"selling_price_list": _name("Price List", "INR")},
			{"selling_price_list": _name("Price List", "USD")},
		])
		settings.validate_unique_combinations("Price List")

		settings.append("price_lists", {"selling_price_list": _name("Price List", "EUR")})
		self.assertRaises(frappe.DuplicateEntryError, settings.validate_unique_combinations, "Price List")

	def test_taxes_overlap(self):
		# example: _Test Cart Tax Template Home Country
		_make_tax_template({"if_address_matches": "Home Country"},
			[{
				"account_head": "_Test Account Service Tax - _TC",
				"charge_type": "On Net Total",
				"description": "Service Tax",
				"rate": 14
			}]
		)
		_make_tax_template({"if_address_matches": "Rest of the World"},
			[{
				"account_head": "_Test Account VAT - _TC",
				"charge_type": "On Net Total",
				"description": "VAT",
				"rate": 6
			}]
		)
		_make_tax_template({
				"if_address_matches": "Rest of the World",
				"title": "_Test Cart Tax Template Rest of the World 2"
			},
			[{
				"account_head": "_Test Account VAT - _TC",
				"charge_type": "On Net Total",
				"description": "VAT", "rate": 12
			}]
		)

		settings = self.get_shopping_cart_settings()
		table_fieldname = settings.doctype_fieldnames["Sales Taxes and Charges Template"]["table_fieldname"]
		link_fieldname = settings.doctype_fieldnames["Sales Taxes and Charges Template"]["link_fieldname"]
		settings.set(table_fieldname, [
			{link_fieldname: _name("Tax Template", "Home Country")},
			{link_fieldname: _name("Tax Template", "Rest of the World")},
		])
		settings.validate_unique_combinations("Sales Taxes and Charges Template")

		settings.append(table_fieldname, {link_fieldname: "_Test Cart Tax Template Rest of the World 2"})
		self.assertRaises(frappe.DuplicateEntryError, settings.validate_unique_combinations, "Sales Taxes and Charges Template")

	def test_exchange_rate_exists(self):
		try:
			frappe.get_doc("Currency Exchange", {"from_currency": "USD", "to_currency": "INR"}).delete()
		except frappe.DoesNotExistError:
			pass

		make_items()
		_make_price_list(_name("Price List", "INR"), "INR", 1, {"if_address_matches": "Home Country"})
		_make_price_list(_name("Price List", "USD"), "USD", 60, {"if_address_matches": "Rest of the World"})

		settings = self.get_shopping_cart_settings()
		settings.set("price_lists", [
			{"selling_price_list": _name("Price List", "INR")},
			{"selling_price_list": _name("Price List", "USD")},
		])
		self.assertRaises(MissingCurrencyExchangeError, settings.validate_exchange_rates)

		from erpnext.setup.doctype.currency_exchange.test_currency_exchange import test_records as \
			currency_exchange_records
		frappe.get_doc(currency_exchange_records[0]).insert()
		settings.validate_exchange_rates()
