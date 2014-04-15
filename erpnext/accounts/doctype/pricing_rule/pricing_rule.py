# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import throw, _
from frappe.model.controller import DocListController

class PricingRule(DocListController):

	def validate(self):
		self.validate_mandatory()
		self.cleanup_fields_value()

	def validate_mandatory(self):
		for field in ["apply_on", "applicable_for", "price_or_discount"]:
			val = self.get("applicable_for")
			if val and not self.get(frappe.scrub(val)):
				throw(_("{0} is required").format(val), frappe.MandatoryError)

	def cleanup_fields_value(self):
		for logic_field in ["apply_on", "applicable_for", "price_or_discount"]:
			fieldname = frappe.scrub(self.get(logic_field) or "")

			# reset all values except for the logic field
			options = (self.meta.get_options(logic_field) or "").split("\n")
			for f in options:
				if not f: continue

				f = frappe.scrub(f)
				if f!=fieldname:
					self.set(f, None)
