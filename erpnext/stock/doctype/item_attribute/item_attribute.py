# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

from erpnext.controllers.item_variant import validate_item_variant_attributes, InvalidItemAttributeValueError


class ItemAttributeIncrementError(frappe.ValidationError): pass

class ItemAttribute(Document):
	def __setup__(self):
		self.flags.ignore_these_exceptions_in_test = [InvalidItemAttributeValueError]

	def validate(self):
		frappe.flags.attribute_values = None
		self.validate_numeric()
		self.validate_duplication()

	def on_update(self):
		self.validate_exising_items()

	def validate_exising_items(self):
		'''Validate that if there are existing items with attributes, they are valid'''
		for item in frappe.db.sql('''select distinct i.name from `tabItem Variant Attribute` iva, `tabItem` i
			where iva.attribute = %s and iva.parent = i.name and i.has_variants = 0''', self.name):
			validate_item_variant_attributes(item[0])

	def validate_numeric(self):
		if self.numeric_values:
			self.set("item_attribute_values", [])
			if self.from_range is None or self.to_range is None:
				frappe.throw(_("Please specify from/to range"))

			elif self.from_range >= self.to_range:
				frappe.throw(_("From Range has to be less than To Range"))

			if not self.increment:
				frappe.throw(_("Increment cannot be 0"), ItemAttributeIncrementError)
		else:
			self.from_range = self.to_range = self.increment = 0

	def validate_duplication(self):
		values, abbrs = [], []
		for d in self.item_attribute_values:
			d.abbr = d.abbr.upper()
			if d.attribute_value in values:
				frappe.throw(_("{0} must appear only once").format(d.attribute_value))
			values.append(d.attribute_value)

			if d.abbr in abbrs:
				frappe.throw(_("{0} must appear only once").format(d.abbr))
			abbrs.append(d.abbr)
