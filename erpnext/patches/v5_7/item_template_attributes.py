# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import print_function, unicode_literals
import frappe
import MySQLdb

def execute():
	"""
		Structure History:
			1. Item and Item Variant
			2. Item, Variant Attribute, Manage Variants and Manage Variant Items
			3. Item, Item Variant Attribute, Item Attribute and Item Attribute Type (latest)
	"""
	rename_and_reload_doctypes()

	variant_templates = frappe.get_all("Item", filters={"has_variants": 1}, limit_page_length=1)
	if not variant_templates:
		# database does not have items that have variants
		# so no point in running the patch
		return

	variant_attributes = frappe.get_all("Item Variant Attribute", fields=["*"], limit_page_length=1)

	if variant_attributes:
		# manage variant patch is already applied
		migrate_manage_variants()

	else:
		# old structure based on "Item Variant" table
		try:
			migrate_item_variants()

		except MySQLdb.ProgrammingError:
			print("`tabItem Variant` not found")

def rename_and_reload_doctypes():
	if "tabVariant Attribute" in frappe.db.get_tables():
		frappe.rename_doc("DocType", "Variant Attribute", "Item Variant Attribute")

	frappe.reload_doctype("Item")
	frappe.reload_doc("Stock", "DocType", "Item Variant Attribute")
	frappe.reload_doc("Stock", "DocType", "Item Attribute Value")
	frappe.reload_doc("Stock", "DocType", "Item Attribute")

def migrate_manage_variants():
	item_attribute = {}
	for d in  frappe.db.sql("""select DISTINCT va.attribute, i.variant_of
		from `tabItem Variant Attribute` va, `tabItem` i
		where va.parent = i.name and ifnull(i.variant_of, '')!=''""", as_dict=1):
		item_attribute.setdefault(d.variant_of, []).append({"attribute": d.attribute})

	for item, attributes in item_attribute.items():
		template = frappe.get_doc("Item", item)
		template.set('attributes', attributes)
		template.save()

# patch old style
def migrate_item_variants():
	for item in frappe.get_all("Item", filters={"has_variants": 1}):
		all_variants = frappe.get_all("Item", filters={"variant_of": item.name}, fields=["name", "description"])
		item_attributes = frappe.db.sql("""select distinct item_attribute, item_attribute_value
			from `tabItem Variant` where parent=%s""", item.name)

		if not item_attributes and not all_variants:
			item = frappe.get_doc("Item", item.name)
			item.has_variants = 0
			item.save()
			continue

		attribute_value_options = {}
		for attribute, value in item_attributes:
			attribute_value_options.setdefault(attribute, []).append(value)

		possible_combinations = get_possible_combinations(attribute_value_options)

		for variant in all_variants:
			for combination in possible_combinations:
				match = True
				for attribute, value in combination.items():
					if "{0}: {1}".format(attribute, value) not in variant.description:
						match = False
						break

				if match:
					# found the right variant
					save_attributes_in_variant(variant, combination)
					break

		save_attributes_in_template(item, attribute_value_options)

	frappe.delete_doc("DocType", "Item Variant")

def save_attributes_in_template(item, attribute_value_options):
	# store attribute in Item Variant Attribute table for template
	template = frappe.get_doc("Item", item)
	template.set("attributes", [{"attribute": attribute} for attribute in attribute_value_options.keys()])
	template.save()

def get_possible_combinations(attribute_value_options):
	possible_combinations = []

	for attribute, values in attribute_value_options.items():
		if not possible_combinations:
			for v in values:
				possible_combinations.append({attribute: v})

		else:
			for v in values:
				for combination in possible_combinations:
					combination[attribute] = v

	return possible_combinations

def save_attributes_in_variant(variant, combination):
	# add data into attributes table
	variant_item = frappe.get_doc("Item", variant.name)
	variant_item.set("attributes", [])
	for attribute, value in combination.items():
		variant_item.append("attributes", {
			"attribute": attribute,
			"attribute_value": value
		})
	variant_item.save()
