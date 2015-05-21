# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
import copy

class DuplicateAttribute(frappe.ValidationError): pass
class ItemTemplateCannotHaveStock(frappe.ValidationError): pass

class ManageVariants(Document):
	
	def generate_combinations(self):
		self.validate_attributes()
		self.validate_template_item()
		self.validate_stock_for_template_must_be_zero()
		self.validate_attribute_values()
		self.validate_attributes_are_unique()
		self.get_variant_item_codes()

	def validate_attributes(self):
		if not self.attributes:
			frappe.throw("Enter atleast one Attribute & its Value in Attribute table.")

	def validate_template_item(self):
		template_item = frappe.get_doc("Item", self.item)
		if not template_item.has_variants:
			frappe.throw(_("Selected Item cannot have Variants."))
			
		if template_item.variant_of:
			frappe.throw(_("Item cannot be a variant of a variant"))

	def validate_stock_for_template_must_be_zero(self):
		stock_in = frappe.db.sql_list("""select warehouse from tabBin
			where item_code=%s and ifnull(actual_qty, 0) > 0""", self.item)
		if stock_in:
			frappe.throw(_("Item Template cannot have stock and varaiants. Please remove \
				stock from warehouses {0}").format(", ".join(stock_in)), ItemTemplateCannotHaveStock)

	def validate_attribute_values(self):
		attributes = {}
		for d in self.attributes:
			attributes.setdefault(d.attribute, 
				[t.attribute_value for t in 
					frappe.db.get_all("Item Attribute Value", fields=["attribute_value"], filters={"parent": d.attribute })])
			if d.attribute_value not in attributes.get(d.attribute):
				frappe.throw(_("Attribute value {0} does not exist in Item Attribute Master.").format(d.attribute_value))

	def validate_attributes_are_unique(self):
		attributes = []
		for d in self.attributes:
			key = (d.attribute, d.attribute_value)
			if key in attributes:
				frappe.throw(_("{0} {1} is entered more than once in Attributes table")
					.format(d.attribute, d.attribute_value), DuplicateAttribute)
			attributes.append(key)

	def get_variant_item_codes(self):
		"""Get all possible suffixes for variants"""
		variant_dict = {}
		variant_item_codes = []

		for d in self.attributes:
			variant_dict.setdefault(d.attribute, []).append(d.attribute_value)

		all_attributes = [d.name for d in frappe.get_all("Item Attribute", order_by = "priority asc")]

		# sort attributes by their priority
		attributes = filter(None, map(lambda d: d if d in variant_dict else None, all_attributes))

		def add_attribute_suffixes(item_code, my_attributes, attributes):
			attr = frappe.get_doc("Item Attribute", attributes[0])
			for value in attr.item_attribute_values:
				if value.attribute_value in variant_dict[attr.name]:
					_my_attributes = copy.deepcopy(my_attributes)
					_my_attributes.append([attr.name, value.attribute_value])
					if len(attributes) > 1:
						add_attribute_suffixes(item_code + "-" + value.abbr, _my_attributes, attributes[1:])
					else:
						variant_item_codes.append(item_code + "-" + value.abbr)

		add_attribute_suffixes(self.item, [], attributes)

		for v in variant_item_codes:
			self.append('variants', {"variant": v})
			
	def create_variants(self):
		pass