# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt


import frappe
from frappe.query_builder.functions import IfNull
from master.master.doctype.item_attribute.item_attribute import ItemAttribute

from erpnext.controllers.item_variant import (
	InvalidItemAttributeValueError,
	validate_is_incremental,
	validate_item_attribute_value,
)


class ERPNextItemAttribute(ItemAttribute):
	def __setup__(self):
		self.flags.ignore_these_exceptions_in_test = [InvalidItemAttributeValueError]

	def on_update(self):
		self.validate_exising_items()

	def validate_exising_items(self):
		"""Validate that if there are existing items with attributes, they are valid"""
		attributes_list = [d.attribute_value for d in self.item_attribute_values]

		# Get Item Variant Attribute details of variant items
		i = frappe.qb.DocType("Item")
		iva = frappe.qb.DocType("Item Variant Attribute")

		items = (
			frappe.qb.from_(iva)
			.from_(i)
			.select(i.name, iva.attribute_value.as_("value"))
			.where((iva.attribute == self.name) & (iva.parent == i.name) & (IfNull(i.variant_of, "") != ""))
		).run(as_dict=True)

		for item in items:
			if self.numeric_values:
				validate_is_incremental(self, self.name, item.value, item.name)
			else:
				validate_item_attribute_value(
					attributes_list, self.name, item.value, item.name, from_variant=False
				)
