# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
import frappe.defaults
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.utils import cint
from master.master.doctype.global_defaults.global_defaults import GlobalDefaults


class ERPNextGlobalDefaults(GlobalDefaults):
	def on_update(self):
		super(ERPNextGlobalDefaults, self).on_update()
		self.toggle_rounded_total()
		self.toggle_in_words()
		frappe.clear_cache()

	def toggle_rounded_total(self):
		self.disable_rounded_total = cint(self.disable_rounded_total)

		# Make property setters to hide rounded total fields
		for doctype in (
			"Quotation",
			"Sales Order",
			"Sales Invoice",
			"Delivery Note",
			"Supplier Quotation",
			"Purchase Order",
			"Purchase Invoice",
			"Purchase Receipt",
		):
			make_property_setter(
				doctype,
				"base_rounded_total",
				"hidden",
				self.disable_rounded_total,
				"Check",
				validate_fields_for_doctype=False,
			)
			make_property_setter(
				doctype, "base_rounded_total", "print_hide", 1, "Check", validate_fields_for_doctype=False
			)

			make_property_setter(
				doctype,
				"rounded_total",
				"hidden",
				self.disable_rounded_total,
				"Check",
				validate_fields_for_doctype=False,
			)
			make_property_setter(
				doctype,
				"rounded_total",
				"print_hide",
				self.disable_rounded_total,
				"Check",
				validate_fields_for_doctype=False,
			)

			make_property_setter(
				doctype,
				"disable_rounded_total",
				"default",
				cint(self.disable_rounded_total),
				"Text",
				validate_fields_for_doctype=False,
			)

	def toggle_in_words(self):
		self.disable_in_words = cint(self.disable_in_words)

		# Make property setters to hide in words fields
		for doctype in (
			"Quotation",
			"Sales Order",
			"Sales Invoice",
			"Delivery Note",
			"Supplier Quotation",
			"Purchase Order",
			"Purchase Invoice",
			"Purchase Receipt",
		):
			make_property_setter(
				doctype,
				"in_words",
				"hidden",
				self.disable_in_words,
				"Check",
				validate_fields_for_doctype=False,
			)
			make_property_setter(
				doctype,
				"in_words",
				"print_hide",
				self.disable_in_words,
				"Check",
				validate_fields_for_doctype=False,
			)
