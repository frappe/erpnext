# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document


class ItemVariantSettings(Document):
	invalid_fields_for_copy_fields_in_variants = ["barcodes"]

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
			"description",
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
				frappe.throw(_("Cannot set the field <b>{0}</b> for copying in variants").format(d.field_name))
