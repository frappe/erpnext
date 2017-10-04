# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class ItemVariantSettings(Document):
	def set_default_fields(self):
		self.fields = []
		fields = frappe.get_meta('Item').fields
		exclude_fields = ["naming_series", "item_code", "item_name", "show_in_website",
			"show_variant_in_website", "standard_rate", "opening_stock", "image", "description",
			"variant_of", "valuation_rate", "description",
			"website_image", "thumbnail", "website_specifiations", "web_long_description"]

		for d in fields:
			if not d.no_copy and d.fieldname not in exclude_fields and \
				d.fieldtype not in ['HTML', 'Section Break', 'Column Break', 'Button', 'Read Only']:
				self.append('fields', {
					'field_name': d.fieldname
				})