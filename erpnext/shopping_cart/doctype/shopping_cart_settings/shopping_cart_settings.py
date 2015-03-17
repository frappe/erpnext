# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, msgprint
from frappe.utils import comma_and
from frappe.model.document import Document
from frappe.utils.nestedset import get_ancestors_of
from erpnext.utilities.doctype.address.address import get_territory_from_address

class ShoppingCartSetupError(frappe.ValidationError): pass

class ShoppingCartSettings(Document):
	def onload(self):
		self.get("__onload").quotation_series = frappe.get_meta("Quotation").get_options("naming_series")

	def validate(self):
		if self.enabled:
			self.validate_price_lists()
			self.validate_tax_masters()
			self.validate_exchange_rates_exist()

	def on_update(self):
		frappe.db.set_default("shopping_cart_enabled", self.get("enabled") or 0)
		frappe.db.set_default("shopping_cart_quotation_series", self.get("quotation_series"))

	def validate_overlapping_territories(self, parentfield, fieldname):
		# for displaying message
		doctype = self.meta.get_field(parentfield).options

		# specify atleast one entry in the table
		self.validate_table_has_rows(parentfield, raise_exception=ShoppingCartSetupError)

		territory_name_map = self.get_territory_name_map(parentfield, fieldname)
		for territory, names in territory_name_map.items():
			if len(names) > 1:
				frappe.throw(_("{0} {1} has a common territory {2}").format(_(doctype), comma_and(names), territory), ShoppingCartSetupError)

		return territory_name_map

	def validate_price_lists(self):
		territory_name_map = self.validate_overlapping_territories("price_lists", "selling_price_list")

		# validate that a Shopping Cart Price List exists for the default territory as a catch all!
		price_list_for_default_territory = self.get_name_from_territory(self.default_territory, "price_lists",
			"selling_price_list")

		if not price_list_for_default_territory:
			msgprint(_("Please specify a Price List which is valid for Territory") +
				": " + self.default_territory, raise_exception=ShoppingCartSetupError)

	def validate_tax_masters(self):
		self.validate_overlapping_territories("sales_taxes_and_charges_masters",
			"sales_taxes_and_charges_master")

	def get_territory_name_map(self, parentfield, fieldname):
		territory_name_map = {}

		# entries in table
		names = [doc.get(fieldname) for doc in self.get(parentfield)]

		if names:
			# for condition in territory check
			parenttype = frappe.get_meta(self.meta.get_options(parentfield)).get_options(fieldname)

			# to validate territory overlap
			# make a map of territory: [list of names]
			# if list against each territory has more than one element, raise exception
			territory_name = frappe.db.sql("""select `territory`, `parent`
				from `tabApplicable Territory`
				where `parenttype`=%s and `parent` in (%s)""" %
				("%s", ", ".join(["%s"]*len(names))), tuple([parenttype] + names))

			for territory, name in territory_name:
				territory_name_map.setdefault(territory, []).append(name)

				if len(territory_name_map[territory]) > 1:
					territory_name_map[territory].sort(key=lambda val: names.index(val))

		return territory_name_map

	def validate_exchange_rates_exist(self):
		"""check if exchange rates exist for all Price List currencies (to company's currency)"""
		company_currency = frappe.db.get_value("Company", self.company, "default_currency")
		if not company_currency:
			msgprint(_("Please specify currency in Company") + ": " + self.company,
				raise_exception=ShoppingCartSetupError)

		price_list_currency_map = frappe.db.get_values("Price List",
			[d.selling_price_list for d in self.get("price_lists")],
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

	def get_name_from_territory(self, territory, parentfield, fieldname):
		name = None
		territory_name_map = self.get_territory_name_map(parentfield, fieldname)

		if territory_name_map.get(territory):
			name = territory_name_map.get(territory)
		else:
			territory_ancestry = self.get_territory_ancestry(territory)
			for ancestor in territory_ancestry:
				if territory_name_map.get(ancestor):
					name = territory_name_map.get(ancestor)
					break

		return name

	def get_price_list(self, billing_territory):
		price_list = self.get_name_from_territory(billing_territory, "price_lists", "selling_price_list")
		return price_list and price_list[0] or None

	def get_tax_master(self, billing_territory):
		tax_master = self.get_name_from_territory(billing_territory, "sales_taxes_and_charges_masters",
			"sales_taxes_and_charges_master")
		return tax_master and tax_master[0] or None

	def get_shipping_rules(self, shipping_territory):
		return self.get_name_from_territory(shipping_territory, "shipping_rules", "shipping_rule")

	def get_territory_ancestry(self, territory):
		if not hasattr(self, "_territory_ancestry"):
			self._territory_ancestry = {}

		if not self._territory_ancestry.get(territory):
			self._territory_ancestry[territory] = get_ancestors_of("Territory", territory)

		return self._territory_ancestry[territory]

def validate_cart_settings(doc, method):
	frappe.get_doc("Shopping Cart Settings", "Shopping Cart Settings").run_method("validate")

def get_shopping_cart_settings():
	if not getattr(frappe.local, "shopping_cart_settings", None):
		frappe.local.shopping_cart_settings = frappe.get_doc("Shopping Cart Settings", "Shopping Cart Settings")

	return frappe.local.shopping_cart_settings

def is_cart_enabled():
	return get_shopping_cart_settings().enabled

def get_default_territory():
	return get_shopping_cart_settings().default_territory

def check_shopping_cart_enabled():
	if not get_shopping_cart_settings().enabled:
		frappe.throw(_("You need to enable Shopping Cart"), ShoppingCartSetupError)

def apply_shopping_cart_settings(quotation, method):
	"""Called via a validate hook on Quotation"""
	from erpnext.shopping_cart import get_party
	if quotation.order_type != "Shopping Cart":
		return

	quotation.billing_territory = (get_territory_from_address(quotation.customer_address)
		or get_party(quotation.contact_email).territory or get_default_territory())
	quotation.shipping_territory = (get_territory_from_address(quotation.shipping_address_name)
		or get_party(quotation.contact_email).territory or get_default_territory())

	set_price_list(quotation)
	set_taxes_and_charges(quotation)
	quotation.calculate_taxes_and_totals()
	set_shipping_rule(quotation)

def set_price_list(quotation):
	previous_selling_price_list = quotation.selling_price_list
	quotation.selling_price_list = get_shopping_cart_settings().get_price_list(quotation.billing_territory)

	if not quotation.selling_price_list:
		quotation.selling_price_list = get_shopping_cart_settings().get_price_list(get_default_territory())

	if previous_selling_price_list != quotation.selling_price_list:
		quotation.price_list_currency = quotation.currency = quotation.plc_conversion_rate = quotation.conversion_rate = None
		for d in quotation.get("items"):
			d.price_list_rate = d.discount_percentage = d.rate = d.amount = None

	quotation.set_price_list_and_item_details()

def set_taxes_and_charges(quotation):
	previous_taxes_and_charges = quotation.taxes_and_charges
	quotation.taxes_and_charges = get_shopping_cart_settings().get_tax_master(quotation.billing_territory)

	if previous_taxes_and_charges != quotation.taxes_and_charges:
		quotation.set_other_charges()

def set_shipping_rule(quotation):
	shipping_rules = get_shopping_cart_settings().get_shipping_rules(quotation.shipping_territory)
	if not shipping_rules:
		quotation.remove_shipping_charge()
		return

	if quotation.shipping_rule not in shipping_rules:
		quotation.remove_shipping_charge()
		quotation.shipping_rule = shipping_rules[0]

	quotation.apply_shipping_rule()
