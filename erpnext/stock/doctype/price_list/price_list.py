# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _, throw
from frappe.model.document import Document
from frappe.utils import cint, now

DEFAULT_PRICE_LIST_SETTINGS = {
	"selling": ("Selling Settings", "selling_price_list"),
	"buying": ("Buying Settings", "buying_price_list"),
}
DEFAULT_PRICE_LIST_HOLDERS = {
	"selling": (
		("Customer", "default_price_list"),
		("Customer Group", "default_price_list"),
		("POS Profile", "selling_price_list"),
	),
	"buying": (("Supplier", "default_price_list"),),
}


class PriceList(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.stock.doctype.price_list_country.price_list_country import PriceListCountry

		buying: DF.Check
		countries: DF.Table[PriceListCountry]
		currency: DF.Link
		enabled: DF.Check
		price_list_name: DF.Data
		price_not_uom_dependent: DF.Check
		selling: DF.Check
	# end: auto-generated types

	def validate(self):
		if not cint(self.buying) and not cint(self.selling):
			throw(_("Price List must be applicable for Buying or Selling"))

		self.validate_currency_change()
		self.validate_side_not_used_as_default("selling")
		self.validate_side_not_used_as_default("buying")

	def validate_side_not_used_as_default(self, side):
		if self.is_new() or cint(self.get(side)) or not cint(self.get_doc_before_save().get(side)):
			return

		if used_in := self.get_doctype_using_as_default(side):
			throw(
				_("Price List {0} is the default in {1}, so it must stay applicable for {2}").format(
					frappe.bold(self.name), _(used_in), get_price_list_side_label(side)
				)
			)

	def get_doctype_using_as_default(self, side):
		settings, fieldname = DEFAULT_PRICE_LIST_SETTINGS[side]
		if frappe.db.get_single_value(settings, fieldname) == self.name:
			return settings

		for doctype, holder_field in DEFAULT_PRICE_LIST_HOLDERS[side]:
			if frappe.db.exists(doctype, {holder_field: self.name}):
				return doctype

	def validate_currency_change(self):
		if self.is_new() or not self.has_value_changed("currency"):
			return

		if item_prices := frappe.db.count("Item Price", {"price_list": self.name}):
			throw(
				_(
					"Currency of Price List {0} cannot be changed because it has {1} Item Prices in {2}. Create a new Price List for {3} instead."
				).format(
					frappe.bold(self.name),
					item_prices,
					frappe.bold(self.get_doc_before_save().currency),
					frappe.bold(self.currency),
				)
			)

	def on_update(self):
		self.set_default_if_missing()
		self.update_item_price()
		self.delete_price_list_details_key()

	def set_default_if_missing(self):
		if cint(self.selling):
			if not frappe.get_single_value("Selling Settings", "selling_price_list"):
				frappe.set_value("Selling Settings", "Selling Settings", "selling_price_list", self.name)

		elif cint(self.buying):
			if not frappe.db.get_single_value("Buying Settings", "buying_price_list"):
				frappe.set_value("Buying Settings", "Buying Settings", "buying_price_list", self.name)

	def update_item_price(self):
		item_price = frappe.qb.DocType("Item Price")
		(
			frappe.qb.update(item_price)
			.set(item_price.currency, self.currency)
			.set(item_price.buying, cint(self.buying))
			.set(item_price.selling, cint(self.selling))
			.set(item_price.modified, now())
			.where(item_price.price_list == self.name)
		).run()

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
		price_list_details = frappe.get_cached_value(
			"Price List", price_list, ["currency", "price_not_uom_dependent", "enabled"], as_dict=1
		)

		if not price_list_details or not price_list_details.get("enabled"):
			throw(_("Price List {0} is disabled or does not exist").format(price_list))

		frappe.cache().hset("price_list_details", price_list, price_list_details)

	return price_list_details or {}


def is_price_list_enabled(price_list: str | None) -> bool:
	return bool(price_list) and bool(frappe.get_cached_value("Price List", price_list, "enabled"))


def validate_default_price_list_side(price_list, side):
	if price_list and not cint(frappe.get_cached_value("Price List", price_list, side)):
		throw(
			_("Default Price List {0} is not applicable for {1}").format(
				frappe.bold(price_list), get_price_list_side_label(side)
			)
		)


def get_price_list_side_label(side):
	return _("Selling") if side == "selling" else _("Buying")


def validate_price_list_country(price_list, country):
	if not price_list or not country:
		return

	countries = frappe.get_all(
		"Price List Country", filters={"parent": price_list, "parenttype": "Price List"}, pluck="country"
	)
	if countries and country not in countries:
		throw(
			_("Price List {0} is not applicable for country {1}").format(
				frappe.bold(price_list), frappe.bold(country)
			)
		)
