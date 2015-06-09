# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import unittest
import frappe

class TestShoppingCart(unittest.TestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		enable_shopping_cart()

	def tearDown(self):
		frappe.set_user("Administrator")
		disable_shopping_cart()

def enable_shopping_cart():
	# Note: Home Country of _Test Company is India
	make_items()
	make_price_lists()
	make_tax_templates()
	make_shipping_rules()

	settings = frappe.get_doc("Shopping Cart Settings")
	settings.company = "_Test Company"
	settings.default_customer_group = "_Test Customer Group"
	settings.quotation_series = "_T-Cart-"

	settings.set("price_lists", [
		{"selling_price_list": _name("Price List", "INR")},
		{"selling_price_list": _name("Price List", "USD")},
	])
	settings.set("sales_taxes_and_charges_masters", [
		{"sales_taxes_and_charges_master": _name("Tax Template", "Home Country")},
		{"sales_taxes_and_charges_master": _name("Tax Template", "Rest of the World")},
	])
	settings.set("shipping_rules", [
		{"shipping_rule": _name("Shipping Rule", "Home Country")},
		{"shipping_rule": _name("Shipping Rule", "Rest of the World")},
	])

	# TODO is this field needed?
	settings.default_territory = "Rest of the World"

	settings.enabled = 1
	settings.save()

def disable_shopping_cart():
	pass

def make_items():
	for i in xrange(5):
		item_code = _name("Item", i+1)
		if frappe.db.exists("Item", item_code):
			continue

		item = frappe.new_doc("Item")
		item.item_code = item_code
		item.insert()

def make_price_lists():
	# example: _Test Cart Price List INR
	_make_price_list(_name("Price List", "INR"), "INR", 1, {"if_address_matches": "Home Country"})
	_make_price_list(_name("Price List", "USD"), "USD", 60, {"if_address_matches": "Rest of the World"})

def _make_price_list(price_list_name, currency, exchange_rate, params):
	if frappe.db.exists("Price List", price_list_name):
		return price_list_name

	price_list = frappe.new_doc("Price List")
	price_list.price_list_name = price_list_name
	price_list.currency = currency
	price_list.update(params)
	price_list.insert()

	for i in xrange(5):
		item_price = frappe.new_doc("Item Price")
		item_price.price_list = price_list.name
		item_price.item_code = _name("Item", i+1)
		item_price.currency = currency
		item_price.price_list_rate = (i+1) * 60.0 / exchange_rate
		item_price.insert()

def make_tax_templates():
	# example: _Test Cart Tax Template Home Country
	_make_tax_template({"if_address_matches": "Home Country"},
		[{"account_head": "_Test Account Service Tax - _TC", "charge_type": "On Net Total", "description": "Service Tax", "rate": 14}])
	_make_tax_template({"if_address_matches": "Rest of the World"},
		[{"account_head": "_Test Account VAT - _TC", "charge_type": "On Net Total", "description": "VAT", "rate": 6}])

def _make_tax_template(params, taxes):
	doctype = "Sales Taxes and Charges Template"
	tax_template_name = _name("Tax Template", params["if_address_matches"])
	if frappe.db.exists(doctype, tax_template_name):
		return

	tax_template = frappe.new_doc(doctype)
	tax_template.title = tax_template_name
	tax_template.set("taxes", taxes)
	tax_template.update(params)
	tax_template.insert()

def make_shipping_rules():
	# example: _Test Cart Shipping Rule Home Country
	# _Test Company's currency is INR
	_make_shipping_rule({"if_address_matches": "Home Country"}, [
		{"from_value": 0, "to_value": 500, "shipping_amount": 100.0},
		{"from_value": 500, "shipping_amount": 0.0},
	])

	# let's make this a flat shipping charge of $20
	_make_shipping_rule({"if_address_matches": "Rest of the World"}, [
		{"from_value": 0, "shipping_amount": 1200}
	])

def _make_shipping_rule(params, conditions):
	shipping_rule_name = _name("Shipping Rule", params["if_address_matches"])
	if frappe.db.exists("Shipping Rule", shipping_rule_name):
		return

	shipping_rule = frappe.new_doc("Shipping Rule")
	shipping_rule.title = shipping_rule_name
	shipping_rule.set("conditions", conditions)
	shipping_rule.update(params)
	shipping_rule.update({
		"account": "_Test Account Shipping Charges - _TC",
	    "calculate_based_on": "Net Total",
	    "company": "_Test Company",
	    "cost_center": "_Test Cost Center - _TC"
	})
	shipping_rule.insert()

def _name(key1, key2):
	return "_Test Cart {0} {1}".format(key1, key2)
