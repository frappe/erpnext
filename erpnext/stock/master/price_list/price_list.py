# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe.utils import cint, now
from master.master.doctype.price_list.price_list import PriceList


class ERPNextPriceList(PriceList):
	def validate(self):
		super(ERPNextPriceList, self).validate()

		if not self.is_new():
			self.check_impact_on_shopping_cart()

	def on_update(self):
		self.set_default_if_missing()
		self.update_item_price()
		super(ERPNextPriceList, self).on_update()

	def update_item_price(self):
		it = frappe.qb.DocType("Item Price")
		(
			frappe.qb.update(it)
			.set(it.currency, self.currency)
			.set(it.buying, cint(self.buying))
			.set(it.selling, cint(self.selling))
			.set(it.modified, now())
			.where(it.price_list == self.name)
		).run()

	def set_default_if_missing(self):
		if cint(self.selling):
			if not frappe.db.get_single_value("Selling Settings", "selling_price_list"):
				frappe.set_value("Selling Settings", "Selling Settings", "selling_price_list", self.name)

		elif cint(self.buying):
			if not frappe.db.get_single_value("Buying Settings", "buying_price_list"):
				frappe.set_value("Buying Settings", "Buying Settings", "buying_price_list", self.name)

	def check_impact_on_shopping_cart(self):
		"Check if Price List currency change impacts E Commerce Cart."
		from erpnext.e_commerce.doctype.e_commerce_settings.e_commerce_settings import (
			validate_cart_settings,
		)

		doc_before_save = self.get_doc_before_save()
		currency_changed = self.currency != doc_before_save.currency
		affects_cart = self.name == frappe.get_cached_value("E Commerce Settings", None, "price_list")

		if currency_changed and affects_cart:
			validate_cart_settings()

	def on_trash(self):
		super(ERPNextPriceList, self).on_trash()

		def _update_default_price_list(module):
			b = frappe.get_doc(module + " Settings")
			price_list_fieldname = module.lower() + "_price_list"

			if self.name == b.get(price_list_fieldname):
				b.set(price_list_fieldname, None)
				b.flags.ignore_permissions = True
				b.save()

		for module in ["Selling", "Buying"]:
			_update_default_price_list(module)
