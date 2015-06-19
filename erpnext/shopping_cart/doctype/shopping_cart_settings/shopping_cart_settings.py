# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cint
from frappe.model.document import Document
from erpnext.utilities.match_address import prepare_filters, validate_unique_combinations

class DocumentNotFoundForCountryError(frappe.ValidationError): pass
class MissingCurrencyExchangeError(frappe.ValidationError): pass

class ShoppingCartSettings(Document):
	def __setup__(self):
		self.doctype_fieldnames = {
			"Price List": {
				"table_fieldname": "price_lists",
				"link_fieldname": "selling_price_list"
			},
			"Sales Taxes and Charges Template": {
				"table_fieldname": "sales_taxes_and_charges_masters",
				"link_fieldname": "sales_taxes_and_charges_master"
			},
			"Shipping Rule": {
				"table_fieldname": "shipping_rules",
				"link_fieldname": "shipping_rule"
			}
		}

	def onload(self):
		self.get("__onload").quotation_series = frappe.get_meta("Quotation").get_options("naming_series")

	def validate(self):
		if not self.enabled:
			return

		self.validate_price_lists()
		self.validate_tax_templates()
		self.validate_shipping_rules()
		self.validate_exchange_rates()

	def validate_price_lists(self):
		self.deduplicate("Price List")
		self.validate_for_countries("Price List")
		self.validate_unique_combinations("Price List")

	def validate_tax_templates(self):
		self.deduplicate("Sales Taxes and Charges Template")
		self.validate_for_countries("Sales Taxes and Charges Template")
		self.validate_unique_combinations("Sales Taxes and Charges Template")

	def validate_shipping_rules(self):
		self.deduplicate("Shipping Rule")
		self.validate_for_countries("Shipping Rule")

	def validate_exchange_rates(self):
		company_currency = frappe.db.get_value("Company", self.company, "default_currency")
		price_list_currencies = list(set([frappe.db.get_value("Price List", d.selling_price_list, "currency")
			for d in self.price_lists]))

		missing_currency_exchange = []
		for currency in price_list_currencies:
			if currency != company_currency and not frappe.db.get_value("Currency Exchange",
				filters={"from_currency": currency, "to_currency": company_currency}):
				missing_currency_exchange.append((currency, company_currency))

		if missing_currency_exchange:
			missing_currency_exchange = ", ".join("{0} - {1}".format(*tup) for tup in missing_currency_exchange)
			frappe.throw(_("You need to create Currency Exchange records for: {0}").format(missing_currency_exchange), MissingCurrencyExchangeError)

	def deduplicate(self, doctype):
		table_fieldname = self.doctype_fieldnames[doctype]["table_fieldname"]
		link_fieldname = self.doctype_fieldnames[doctype]["link_fieldname"]
		new_list = []
		names = []
		for d in self.get(table_fieldname):
			if d.get(link_fieldname) not in names:
				new_list.append(d)
				names.append(d.get(link_fieldname))

		if len(self.get(table_fieldname)) != len(new_list):
			self.set(table_fieldname, new_list)

	def validate_for_countries(self, doctype):
		table_fieldname = self.doctype_fieldnames[doctype]["table_fieldname"]
		link_fieldname = self.doctype_fieldnames[doctype]["link_fieldname"]

		# eg. names of price lists selected in Shopping Cart Settings
		names = [d.get(link_fieldname) for d in self.get(table_fieldname)]
		if not names:
			return

		if self.countries:
			# if countries are listed, check that record exists for the mentioned countries
			self.validate_for_specific_country(doctype, names)
		else:
			# if countries are not listed, check if "Any Country" or ("Home Country" and "Rest of the World") combination exists
			self.validate_for_any_country(doctype, names)

	def validate_for_specific_country(self, doctype, names):
		home_country = frappe.db.get_value("Company", self.company, "country")

		for country in self.countries:
			country = country.country
			results = frappe.get_all(doctype, filters=prepare_filters(doctype, self.company, {
				"if_address_matches": "Country, State, Postal Code Pattern",
				"country": country,
				"state": "",
				"postal_code_pattern": "",
				"name": ("in", names)
			}))

			if not results and country==home_country:
				results = frappe.get_all(doctype, filters=prepare_filters(doctype, self.company, {
					"if_address_matches": "Home Country",
					"name": ("in", names)
				}))
				if not results:
					frappe.throw(_("Please select a '{0}' which has 'If Address Matches' as 'Home Country'").format(doctype), DocumentNotFoundForCountryError)

			if not results:
				frappe.throw(_("Please select a '{0}' which has 'If Address Matches' as 'Country, State, Post Code Pattern', 'Country' as '{1}', and 'State' and 'Post Code Pattern' as blank").format(doctype, country), DocumentNotFoundForCountryError)

	def validate_for_any_country(self, doctype, names):
		any_country = frappe.get_all(doctype, filters=prepare_filters(doctype, self.company, {
			"if_address_matches": "Any Country",
			"name": ("in", names)
		}))

		if not any_country:
			home_country = frappe.get_all(doctype, filters=prepare_filters(doctype, self.company, {
				"if_address_matches": "Home Country",
				"name": ("in", names)
			}))

			rest_of_the_world = frappe.get_all(doctype, filters=prepare_filters(doctype, self.company, {
				"if_address_matches": "Rest of the World",
				"name": ("in", names)
			}))

			if not (home_country and rest_of_the_world):
				frappe.throw(_("Please select a '{0}' which has 'If Address Matches' as 'Any Country'").format(doctype), DocumentNotFoundForCountryError)

	def validate_unique_combinations(self, doctype):
		table_fieldname = self.doctype_fieldnames[doctype]["table_fieldname"]
		link_fieldname = self.doctype_fieldnames[doctype]["link_fieldname"]
		names = [d.get(link_fieldname) for d in self.get(table_fieldname)]
		for name in names:
			doc = frappe.get_doc(doctype, name)

			# we determine other_names because "name" != current_name filter is being replaced in validate_unique_combinations queries
			other_names = [n for n in names if n!=name]

			validate_unique_combinations(doc, additional_filters={"name": ("in", other_names)})

def validate_cart_settings(doc, method):
	frappe.get_doc("Shopping Cart Settings", "Shopping Cart Settings").run_method("validate")

def is_cart_enabled():
	return cint(frappe.db.get_value("Shopping Cart Settings", "Shopping Cart Settings", "enabled"))

@frappe.whitelist()
def add_to_shopping_cart_settings(doctype, name):
	settings = frappe.get_doc("Shopping Cart Settings")
	table_fieldname = settings.doctype_fieldnames[doctype]["table_fieldname"]
	link_fieldname = settings.doctype_fieldnames[doctype]["link_fieldname"]
	settings.append(table_fieldname, {link_fieldname: name})
	settings.save()

def onload_for_shopping_cart_settings(doc):
	settings = frappe.get_doc("Shopping Cart Settings")
	table_fieldname = settings.doctype_fieldnames[doc.doctype]["table_fieldname"]
	link_fieldname = settings.doctype_fieldnames[doc.doctype]["link_fieldname"]

	for d in settings.get(table_fieldname):
		if d.get(link_fieldname)==doc.name:
			doc.get("__onload").in_shopping_cart = True
			break
