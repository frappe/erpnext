# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from erpnext.controllers.item_variant import (
	InvalidItemAttributeValueError,
	update_variant_attribute_values,
	update_variant_item_codes_for_abbr_renames,
	validate_is_incremental,
	validate_item_attribute_value,
)


class ItemAttributeIncrementError(frappe.ValidationError):
	pass


class ItemAttribute(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.stock.doctype.item_attribute_value.item_attribute_value import ItemAttributeValue

		attribute_name: DF.Data
		disabled: DF.Check
		from_range: DF.Float
		increment: DF.Float
		item_attribute_values: DF.Table[ItemAttributeValue]
		numeric_values: DF.Check
		to_range: DF.Float
	# end: auto-generated types

	def validate(self):
		frappe.flags.attribute_values = None
		self.validate_numeric_change()
		self.validate_numeric()
		self.validate_duplication()

	def on_update(self):
		update_variant_attribute_values(self)
		update_variant_item_codes_for_abbr_renames(self)
		self.validate_exising_items()
		self.set_enabled_disabled_in_items()

	def set_enabled_disabled_in_items(self):
		db_value = self.get_doc_before_save()
		if not db_value or db_value.disabled != self.disabled:
			item_variant_table = frappe.qb.DocType("Item Variant Attribute")
			query = (
				frappe.qb.update(item_variant_table)
				.set(item_variant_table.disabled, self.disabled)
				.where(item_variant_table.attribute == self.name)
			)

			query.run()

	def get_variants_using_attribute(self, limit=None):
		iva = frappe.qb.DocType("Item Variant Attribute")
		i = frappe.qb.DocType("Item")
		query = (
			frappe.qb.from_(iva)
			.inner_join(i)
			.on(iva.parent == i.name)
			.select(i.name, iva.attribute_value.as_("value"))
			.where((iva.attribute == self.name) & i.variant_of.isnotnull() & (i.variant_of != ""))
		)

		return query.limit(limit).run(as_dict=1) if limit else query.run(as_dict=1)

	def validate_exising_items(self):
		"""Validate that if there are existing items with attributes, they are valid"""
		attributes_list = [d.attribute_value for d in self.item_attribute_values]
		removed_values = self.get_removed_attribute_values(attributes_list)

		for item in self.get_variants_using_attribute():
			if self.numeric_values:
				validate_is_incremental(self, self.name, item.value, item.name)
			elif item.value in removed_values:
				validate_item_attribute_value(
					attributes_list, self.name, item.value, item.name, from_variant=False
				)

	def get_removed_attribute_values(self, attributes_list):
		previous = self.get_doc_before_save()
		if not previous:
			return set()

		return {d.attribute_value for d in previous.item_attribute_values} - set(attributes_list)

	def validate_numeric_change(self):
		if self.is_new() or not self.has_value_changed("numeric_values"):
			return

		if self.get_variants_using_attribute(limit=1):
			frappe.throw(
				_("Numeric Values cannot be changed for Attribute {0} as it is used in variants").format(
					frappe.bold(self.name)
				)
			)

	def validate_numeric(self):
		if self.numeric_values:
			self.set("item_attribute_values", [])
			if self.from_range is None or self.to_range is None:
				frappe.throw(_("Please specify from/to range"))

			elif flt(self.from_range) >= flt(self.to_range):
				frappe.throw(_("From Range has to be less than To Range"))

			if not self.increment:
				frappe.throw(_("Increment cannot be 0"), ItemAttributeIncrementError)
		else:
			self.from_range = self.to_range = self.increment = 0

	def validate_duplication(self):
		values, abbrs = [], []
		for d in self.item_attribute_values:
			if d.attribute_value.lower() in map(str.lower, values):
				frappe.throw(
					_("Attribute value: {0} must appear only once").format(d.attribute_value.title())
				)
			values.append(d.attribute_value)

			if d.abbr.lower() in map(str.lower, abbrs):
				frappe.throw(_("Abbreviation: {0} must appear only once").format(d.abbr.title()))
			abbrs.append(d.abbr)
