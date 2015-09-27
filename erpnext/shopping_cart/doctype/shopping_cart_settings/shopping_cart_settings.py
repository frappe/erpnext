# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, msgprint
from frappe.utils import comma_and
from frappe.model.document import Document

class ShoppingCartSetupError(frappe.ValidationError): pass

class ShoppingCartSettings(Document):
	def onload(self):
		self.get("__onload").quotation_series = frappe.get_meta("Quotation").get_options("naming_series")

	def validate(self):
		if self.enabled:
			self.validate_exchange_rates_exist()

	def validate_exchange_rates_exist(self):
		"""check if exchange rates exist for all Price List currencies (to company's currency)"""
		company_currency = frappe.db.get_value("Company", self.company, "default_currency")
		if not company_currency:
			msgprint(_("Please specify currency in Company") + ": " + self.company,
				raise_exception=ShoppingCartSetupError)

		price_list_currency_map = frappe.db.get_values("Price List",
			[self.price_list],
			"currency")

		# check if all price lists have a currency
		for price_list, currency in price_list_currency_map.items():
			if not currency:
				frappe.throw(_("Currency is required for Price List {0}").format(price_list))

		expected_to_exist = [currency + "-" + company_currency
			for currency in price_list_currency_map.values()
			if currency != company_currency]

		if expected_to_exist:
			exists = frappe.db.sql_list("""select name from `tabCurrency Exchange`
				where name in (%s)""" % (", ".join(["%s"]*len(expected_to_exist)),),
				tuple(expected_to_exist))

			missing = list(set(expected_to_exist).difference(exists))

			if missing:
				msgprint(_("Missing Currency Exchange Rates for {0}").format(comma_and(missing)),
					raise_exception=ShoppingCartSetupError)

	def validate_tax_rule(self):
		if not frappe.db.get_value("Tax Rule", {"use_for_shopping_cart" : 1}, "name"):
			frappe.throw(frappe._("Set Tax Rule for shopping cart"), ShoppingCartSetupError)

	def get_tax_master(self, billing_territory):
		tax_master = self.get_name_from_territory(billing_territory, "sales_taxes_and_charges_masters",
			"sales_taxes_and_charges_master")
		return tax_master and tax_master[0] or None

	def get_shipping_rules(self, shipping_territory):
		return self.get_name_from_territory(shipping_territory, "shipping_rules", "shipping_rule")

def validate_cart_settings(doc, method):
	frappe.get_doc("Shopping Cart Settings", "Shopping Cart Settings").run_method("validate")

def get_shopping_cart_settings():
	if not getattr(frappe.local, "shopping_cart_settings", None):
		frappe.local.shopping_cart_settings = frappe.get_doc("Shopping Cart Settings", "Shopping Cart Settings")

	return frappe.local.shopping_cart_settings

def is_cart_enabled():
	return get_shopping_cart_settings().enabled

def check_shopping_cart_enabled():
	if not get_shopping_cart_settings().enabled:
		frappe.throw(_("You need to enable Shopping Cart"), ShoppingCartSetupError)

