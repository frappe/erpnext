# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import typing

import frappe
from frappe import _
from frappe.model.document import Document


class ItemVariantSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.stock.doctype.variant_field.variant_field import VariantField

		allow_different_uom: DF.Check
		allow_rename_attribute_value: DF.Check
		do_not_update_variants: DF.Check
		fields: DF.Table[VariantField]
	# end: auto-generated types

	invalid_fields_for_copy_fields_in_variants: typing.ClassVar[list] = ["barcodes"]

	def set_default_fields(self):
		self.fields = []
		fields = frappe.get_meta("Item").fields
		exclude_fields = {
			"naming_series",
			"item_code",
			"item_name",
			"published_in_website",
			"standard_rate",
			"opening_stock",
			"image",
			"description",
			"variant_of",
			"valuation_rate",
			"barcodes",
			"has_variants",
			"attributes",
		}

		for d in fields:
			if (
				not d.no_copy
				and d.fieldname not in exclude_fields
				and d.fieldtype not in ["HTML", "Section Break", "Column Break", "Button", "Read Only"]
			):
				self.append("fields", {"field_name": d.fieldname})

	def remove_invalid_fields_for_copy_fields_in_variants(self):
		fields = [
			row
			for row in self.fields
			if row.field_name not in self.invalid_fields_for_copy_fields_in_variants
		]
		self.fields = fields
		self.save()

	def validate(self):
		for d in self.fields:
			if d.field_name in self.invalid_fields_for_copy_fields_in_variants:
				frappe.throw(
					_("Cannot set the field <b>{0}</b> for copying in variants").format(d.field_name)
				)
