# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


"""Global Defaults"""

import frappe
import frappe.defaults
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.utils import cint

keydict = {
	# "key in defaults": "key in Global Defaults"
	"company": "default_company",
	"currency": "default_currency",
	"country": "country",
	"hide_currency_symbol": "hide_currency_symbol",
	"account_url": "account_url",
	"disable_rounded_total": "disable_rounded_total",
	"disable_in_words": "disable_in_words",
}

ROUNDED_TOTAL_DOCTYPES = (
	"Quotation",
	"Sales Order",
	"POS Invoice",
	"Sales Invoice",
	"Delivery Note",
	"Supplier Quotation",
	"Purchase Order",
	"Purchase Invoice",
	"Purchase Receipt",
)
IN_WORDS_DOCTYPES = (*ROUNDED_TOTAL_DOCTYPES, "Payment Entry", "Subcontracting Receipt")

from frappe.model.document import Document


class GlobalDefaults(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		country: DF.Link | None
		default_company: DF.Link | None
		default_currency: DF.Link
		default_distance_unit: DF.Link | None
		demo_company: DF.Link | None
		disable_in_words: DF.Check
		disable_rounded_total: DF.Check
		hide_currency_symbol: DF.Check
		use_posting_datetime_for_naming_documents: DF.Check
	# end: auto-generated types

	def on_update(self):
		"""update defaults"""
		for key in keydict:
			frappe.db.set_default(key, self.get(keydict[key], ""))

		# enable default currency
		if self.default_currency:
			frappe.db.set_value("Currency", self.default_currency, "enabled", 1)

		self.toggle_rounded_total()
		self.toggle_in_words()
		if self.has_value_changed("disable_rounded_total"):
			self.set_disable_rounded_total_on_pos_profiles()

		frappe.clear_cache()

	@frappe.whitelist()
	def get_defaults(self):
		return frappe.defaults.get_defaults()

	def toggle_rounded_total(self):
		self.sync_property_setters(
			ROUNDED_TOTAL_DOCTYPES,
			[
				("base_rounded_total", "hidden", "Check"),
				("rounded_total", "hidden", "Check"),
				("rounded_total", "print_hide", "Check"),
				("disable_rounded_total", "default", "Text"),
			],
			cint(self.disable_rounded_total),
		)

	def toggle_in_words(self):
		self.sync_property_setters(
			IN_WORDS_DOCTYPES,
			[("in_words", "hidden", "Check"), ("in_words", "print_hide", "Check")],
			cint(self.disable_in_words),
		)

	def sync_property_setters(self, doctypes, properties, value):
		for doctype in doctypes:
			meta = frappe.get_meta(doctype)
			for fieldname, property, property_type in properties:
				field = meta.get_field(fieldname)
				if field and cint(field.get(property)) != value:
					make_property_setter(
						doctype,
						fieldname,
						property,
						value,
						property_type,
						validate_fields_for_doctype=False,
					)

	def set_disable_rounded_total_on_pos_profiles(self):
		POSProfile = frappe.qb.DocType("POS Profile")

		frappe.qb.update(POSProfile).set(
			POSProfile.disable_rounded_total, cint(self.disable_rounded_total)
		).run()
