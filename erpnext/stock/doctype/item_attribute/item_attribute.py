# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class ItemAttributeIncrementError(frappe.ValidationError): pass

class ItemAttribute(Document):
	def validate(self):
		self.validate_numeric()
		self.validate_duplication()
		self.validate_attribute_values()

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

	def validate_attribute_values(self):
		attribute_values = []
		for d in self.item_attribute_values:
			attribute_values.append(d.attribute_value)

		variant_attributes = frappe.db.sql("select DISTINCT attribute_value from `tabItem Variant Attribute` where attribute=%s", self.name)
		if variant_attributes:
			for d in variant_attributes:
				if d[0] and d[0] not in attribute_values:
					frappe.throw(_("Attribute Value {0} cannot be removed from {1} as Item Variants \
						exist with this Attribute.").format(d[0], self.name))
