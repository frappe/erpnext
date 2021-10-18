# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe import _, throw
from frappe.model.document import Document
from frappe.utils import cint


class PriceList(Document):
	def validate(self):
		if not cint(self.buying) and not cint(self.selling):
			throw(_("Price List must be applicable for Buying or Selling"))

		if not self.is_new():
			self.check_impact_on_shopping_cart()

	def on_update(self):
		self.set_default_if_missing()
		self.update_item_price()
		self.delete_price_list_details_key()

	def set_default_if_missing(self):
		if cint(self.selling):
			if not frappe.db.get_value("Selling Settings", None, "selling_price_list"):
				frappe.set_value("Selling Settings", "Selling Settings", "selling_price_list", self.name)

		elif cint(self.buying):
			if not frappe.db.get_value("Buying Settings", None, "buying_price_list"):
				frappe.set_value("Buying Settings", "Buying Settings", "buying_price_list", self.name)

	def update_item_price(self):
		frappe.db.sql("""update `tabItem Price` set currency=%s,
			buying=%s, selling=%s, modified=NOW() where price_list=%s""",
			(self.currency, cint(self.buying), cint(self.selling), self.name))

	def check_impact_on_shopping_cart(self):
		"Check if Price List currency change impacts Shopping Cart."
		from erpnext.shopping_cart.doctype.shopping_cart_settings.shopping_cart_settings import (
			validate_cart_settings,
		)

		doc_before_save = self.get_doc_before_save()
		currency_changed = self.currency != doc_before_save.currency
		affects_cart = self.name == frappe.get_cached_value("Shopping Cart Settings", None, "price_list")

		if currency_changed and affects_cart:
			validate_cart_settings()

	def on_trash(self):
		self.delete_price_list_details_key()

		def _update_default_price_list(module):
			b = frappe.get_doc(module + " Settings")
			price_list_fieldname = module.lower() + "_price_list"

			if self.name == b.get(price_list_fieldname):
				b.set(price_list_fieldname, None)
				b.flags.ignore_permissions = True
				b.save()

		for module in ["Selling", "Buying"]:
			_update_default_price_list(module)

	def delete_price_list_details_key(self):
		frappe.cache().hdel("price_list_details", self.name)

def get_price_list_details(price_list):
	price_list_details = frappe.cache().hget("price_list_details", price_list)

	if not price_list_details:
		price_list_details = frappe.get_cached_value("Price List", price_list,
			["currency", "price_not_uom_dependent", "enabled"], as_dict=1)

		if not price_list_details or not price_list_details.get("enabled"):
			throw(_("Price List {0} is disabled or does not exist").format(price_list))

		frappe.cache().hset("price_list_details", price_list, price_list_details)

	return price_list_details or {}
