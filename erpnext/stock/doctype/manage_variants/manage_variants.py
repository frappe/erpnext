# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
import copy
import json

class DuplicateAttribute(frappe.ValidationError): pass
class ItemTemplateCannotHaveStock(frappe.ValidationError): pass

class ManageVariants(Document):

	def get_item_details(self):
		self.get_attributes()
		self.get_variants()
		
	def generate_combinations(self):
		self.validate_attributes()
		self.validate_template_item()
		self.validate_stock_for_template_must_be_zero()
		self.validate_attribute_values()
		self.validate_attributes_are_unique()
		self.get_variant_item_codes()
		
	def create_variants(self):
		self.sync_variants()
	
	def get_attributes(self):
		attributes = {}
		self.set('attributes', [])
		for d in frappe.db.sql("""select attribute, attribute_value from `tabVariant Attribute` as attribute, 
			`tabItem` as item where attribute.parent= item.name and item.variant_of = %s""", self.item, as_dict=1):
				attributes.setdefault(d.attribute, []).append(d.attribute_value)
		for d in attributes:
			attribute_values = set(attributes[d])
			for value in attribute_values:
				self.append('attributes',{"attribute": d, "attribute_value": value})

	def get_variants(self):
		self.set('variants', [])
		variants = [d.name for d in frappe.get_all("Item",
			filters={"variant_of":self.item})]
		for d in variants:
			variant_attributes, attributes = "", []
			for attribute in frappe.db.sql("""select attribute, attribute_value from `tabVariant Attribute` where parent = %s""", d):
				variant_attributes += attribute[1] + " "
				attributes.append([attribute[0], attribute[1]])
			self.append('variants',{"variant": d, "variant_attributes": variant_attributes, "attributes": json.dumps(attributes)})

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
		self.set('variants', [])

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
						variant_attributes = ""
						for d in _my_attributes:
							variant_attributes += d[1] + " "
						self.append('variants', {"variant": item_code + "-" + value.abbr, 
							"attributes": json.dumps(_my_attributes), "variant_attributes": variant_attributes})

		add_attribute_suffixes(self.item, [], attributes)

	def sync_variants(self):
		variant_item_codes = []
		for v in self.variants:
			variant_item_codes.append(v.variant)

		existing_variants = [d.name for d in frappe.get_all("Item",
			filters={"variant_of":self.item})]

		inserted, updated, deleted = [], [], []
		for existing_variant in existing_variants:
			if existing_variant not in variant_item_codes:
				frappe.delete_doc("Item", existing_variant)
				deleted.append(existing_variant)

		for item_code in variant_item_codes:
			if item_code not in existing_variants:
				make_variant(self.item, item_code, self.variants)
				inserted.append(item_code)
			else:
				update_variant(self.item, existing_variant, self.variants)
				updated.append(existing_variant)

		if inserted:
			frappe.msgprint(_("Item Variants {0} created").format(", ".join(inserted)))

		if updated:
			frappe.msgprint(_("Item Variants {0} updated").format(", ".join(updated)))

		if deleted:
			frappe.msgprint(_("Item Variants {0} deleted").format(", ".join(deleted)))
	
def make_variant(item, variant_code, variant_attribute):
	variant = frappe.new_doc("Item")
	variant.item_code = variant_code
	template = frappe.get_doc("Item", item)
	copy_attributes_to_variant(template, variant, variant_attribute, insert=True)
	variant.insert()

def update_variant(item, variant_code, variant_attribute=None):
	variant = frappe.get_doc("Item", variant_code)
	template = frappe.get_doc("Item", item)
	copy_attributes_to_variant(template, variant, variant_attribute, insert=True)
	variant.save()

def copy_attributes_to_variant(template, variant, variant_attribute=None, insert=False):
	from frappe.model import no_value_fields
	for field in template.meta.fields:
		if field.fieldtype not in no_value_fields and (insert or not field.no_copy)\
			and field.fieldname not in ("item_code", "item_name"):
			if variant.get(field.fieldname) != template.get(field.fieldname):
				variant.set(field.fieldname, template.get(field.fieldname))
	variant.item_name = template.item_name + variant.item_code[len(template.name):]
	variant.variant_of = template.name
	variant.has_variants = 0
	variant.show_in_website = 0
	if variant_attribute:
		for d in variant_attribute:
			if d.variant == variant.item_code:
				variant.attributes= []
				for a in json.loads(d.attributes):
					variant.append('attributes', {"attribute": a[0], "attribute_value": a[1]})
	if variant.attributes:
		variant.description += "\n"
		for d in variant.attributes:
			variant.description += "<p>" + d.attribute + ": " + d.attribute_value + "</p>"