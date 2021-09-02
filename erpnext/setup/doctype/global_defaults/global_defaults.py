# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

"""Global Defaults"""
import frappe
import frappe.defaults
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.utils import cint

keydict = {
	# "key in defaults": "key in Global Defaults"
	"fiscal_year": "current_fiscal_year",
	'company': 'default_company',
	'currency': 'default_currency',
	"country": "country",
	'hide_currency_symbol':'hide_currency_symbol',
	'account_url':'account_url',
	'disable_rounded_total': 'disable_rounded_total',
	'disable_in_words': 'disable_in_words',
}

from frappe.model.document import Document


class GlobalDefaults(Document):

	def on_update(self):
		"""update defaults"""
		for key in keydict:
			frappe.db.set_default(key, self.get(keydict[key], ''))

		# update year start date and year end date from fiscal_year
		year_start_end_date = frappe.db.sql("""select year_start_date, year_end_date
			from `tabFiscal Year` where name=%s""", self.current_fiscal_year)
		if year_start_end_date:
			ysd = year_start_end_date[0][0] or ''
			yed = year_start_end_date[0][1] or ''

			if ysd and yed:
				frappe.db.set_default('year_start_date', ysd.strftime('%Y-%m-%d'))
				frappe.db.set_default('year_end_date', yed.strftime('%Y-%m-%d'))

		# enable default currency
		if self.default_currency:
			frappe.db.set_value("Currency", self.default_currency, "enabled", 1)

		self.toggle_rounded_total()
		self.toggle_in_words()

		# clear cache
		frappe.clear_cache()

	@frappe.whitelist()
	def get_defaults(self):
		return frappe.defaults.get_defaults()

	def toggle_rounded_total(self):
		self.disable_rounded_total = cint(self.disable_rounded_total)

		# Make property setters to hide rounded total fields
		for doctype in ("Quotation", "Sales Order", "Sales Invoice", "Delivery Note",
			"Supplier Quotation", "Purchase Order", "Purchase Invoice", "Purchase Receipt"):
			make_property_setter(doctype, "base_rounded_total", "hidden", self.disable_rounded_total, "Check", validate_fields_for_doctype=False)
			make_property_setter(doctype, "base_rounded_total", "print_hide", 1, "Check", validate_fields_for_doctype=False)

			make_property_setter(doctype, "rounded_total", "hidden", self.disable_rounded_total, "Check", validate_fields_for_doctype=False)
			make_property_setter(doctype, "rounded_total", "print_hide", self.disable_rounded_total, "Check", validate_fields_for_doctype=False)

			make_property_setter(doctype, "disable_rounded_total", "default", cint(self.disable_rounded_total), "Text", validate_fields_for_doctype=False)

	def toggle_in_words(self):
		self.disable_in_words = cint(self.disable_in_words)

		# Make property setters to hide in words fields
		for doctype in ("Quotation", "Sales Order", "Sales Invoice", "Delivery Note",
				"Supplier Quotation", "Purchase Order", "Purchase Invoice", "Purchase Receipt"):
			make_property_setter(doctype, "in_words", "hidden", self.disable_in_words, "Check", validate_fields_for_doctype=False)
			make_property_setter(doctype, "in_words", "print_hide", self.disable_in_words, "Check", validate_fields_for_doctype=False)
