# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cstr, flt
import json

class ItemVariantExistsError(frappe.ValidationError): pass
class InvalidItemAttributeValueError(frappe.ValidationError): pass
class ItemTemplateCannotHaveStock(frappe.ValidationError): pass

@frappe.whitelist()
def get_variant(template, args, variant=None):
	"""Validates Attributes and their Values, then looks for an exactly matching Item Variant

		:param item: Template Item
		:param args: A dictionary with "Attribute" as key and "Attribute Value" as value
	"""
	if isinstance(args, basestring):
		args = json.loads(args)

	if not args:
		frappe.throw(_("Please specify at least one attribute in the Attributes table"))

	return find_variant(template, args, variant)

def validate_item_variant_attributes(item, args=None):
	if isinstance(item, basestring):
		item = frappe.get_doc('Item', item)

	if not args:
		args = {d.attribute.lower():d.attribute_value for d in item.attributes}

	attribute_values, numeric_values = get_attribute_values()

	for attribute, value in args.items():
		if not value:
			continue

		if attribute.lower() in numeric_values:
			numeric_attribute = numeric_values[attribute.lower()]

			from_range = numeric_attribute.from_range
			to_range = numeric_attribute.to_range
			increment = numeric_attribute.increment

			if increment == 0:
				# defensive validation to prevent ZeroDivisionError
				frappe.throw(_("Increment for Attribute {0} cannot be 0").format(attribute))

			is_in_range = from_range <= flt(value) <= to_range
			precision = max(len(cstr(v).split(".")[-1].rstrip("0")) for v in (value, increment))
			#avoid precision error by rounding the remainder
			remainder = flt((flt(value) - from_range) % increment, precision)

			is_incremental = remainder==0 or remainder==increment

			if not (is_in_range and is_incremental):
				frappe.throw(_("Value for Attribute {0} must be within the range of {1} to {2} in the increments of {3} for Item {4}")\
					.format(attribute, from_range, to_range, increment, item.name),
					InvalidItemAttributeValueError, title=_('Invalid Attribute'))

		elif value not in attribute_values.get(attribute.lower(), []):
			frappe.throw(_("Value {0} for Attribute {1} does not exist in the list of valid Item Attribute Values for Item {2}").format(
				value, attribute, item.name), InvalidItemAttributeValueError, title=_('Invalid Attribute'))

def get_attribute_values():
	if not frappe.flags.attribute_values:
		attribute_values = {}
		numeric_values = {}
		for t in frappe.get_all("Item Attribute Value", fields=["parent", "attribute_value"]):
			attribute_values.setdefault(t.parent.lower(), []).append(t.attribute_value)

		for t in frappe.get_all('Item Attribute',
			fields=["name", "from_range", "to_range", "increment"], filters={'numeric_values': 1}):
			numeric_values[t.name.lower()] = t

		frappe.flags.attribute_values = attribute_values
		frappe.flags.numeric_values = numeric_values

	return frappe.flags.attribute_values, frappe.flags.numeric_values

def find_variant(template, args, variant_item_code=None):
	conditions = ["""(iv_attribute.attribute="{0}" and iv_attribute.attribute_value="{1}")"""\
		.format(frappe.db.escape(key), frappe.db.escape(cstr(value))) for key, value in args.items()]

	conditions = " or ".join(conditions)

	# use approximate match and shortlist possible variant matches
	# it is approximate because we are matching using OR condition
	# and it need not be exact match at this stage
	# this uses a simpler query instead of using multiple exists conditions
	possible_variants = frappe.db.sql_list("""select name from `tabItem` item
		where variant_of=%s and exists (
			select name from `tabItem Variant Attribute` iv_attribute
				where iv_attribute.parent=item.name
				and ({conditions}) and parent != %s
		)""".format(conditions=conditions), (template, cstr(variant_item_code)))

	for variant in possible_variants:
		variant = frappe.get_doc("Item", variant)

		if len(args.keys()) == len(variant.get("attributes")):
			# has the same number of attributes and values
			# assuming no duplication as per the validation in Item
			match_count = 0

			for attribute, value in args.items():
				for row in variant.attributes:
					if row.attribute==attribute and row.attribute_value== cstr(value):
						# this row matches
						match_count += 1
						break

			if match_count == len(args.keys()):
				return variant.name

@frappe.whitelist()
def create_variant(item, args):
	if isinstance(args, basestring):
		args = json.loads(args)

	template = frappe.get_doc("Item", item)
	variant = frappe.new_doc("Item")
	variant_attributes = []

	for d in template.attributes:
		variant_attributes.append({
			"attribute": d.attribute,
			"attribute_value": args.get(d.attribute)
		})

	variant.set("attributes", variant_attributes)
	copy_attributes_to_variant(template, variant)
	make_variant_item_code(template.item_code, variant)

	return variant

def copy_attributes_to_variant(item, variant):
	from frappe.model import no_value_fields
	for field in item.meta.fields:
		if field.fieldtype not in no_value_fields and (not field.no_copy)\
			and field.fieldname not in ("item_code", "item_name", "show_in_website"):
			if variant.get(field.fieldname) != item.get(field.fieldname):
				variant.set(field.fieldname, item.get(field.fieldname))
	variant.variant_of = item.name
	variant.has_variants = 0
	if variant.attributes:
		variant.description += "\n"
		for d in variant.attributes:
			variant.description += "<p>" + d.attribute + ": " + cstr(d.attribute_value) + "</p>"

def make_variant_item_code(template_item_code, variant):
	"""Uses template's item code and abbreviations to make variant's item code"""
	if variant.item_code:
		return

	abbreviations = []
	for attr in variant.attributes:
		item_attribute = frappe.db.sql("""select i.numeric_values, v.abbr
			from `tabItem Attribute` i left join `tabItem Attribute Value` v
				on (i.name=v.parent)
			where i.name=%(attribute)s and v.attribute_value=%(attribute_value)s""", {
				"attribute": attr.attribute,
				"attribute_value": attr.attribute_value
			}, as_dict=True)

		if not item_attribute:
			return
			# frappe.throw(_('Invalid attribute {0} {1}').format(frappe.bold(attr.attribute),
			# 	frappe.bold(attr.attribute_value)), title=_('Invalid Attribute'),
			# 	exc=InvalidItemAttributeValueError)

		if item_attribute[0].numeric_values:
			# don't generate item code if one of the attributes is numeric
			return

		abbreviations.append(item_attribute[0].abbr)

	if abbreviations:
		variant.item_code = "{0}-{1}".format(template_item_code, "-".join(abbreviations))

	if variant.item_code:
		variant.item_name = variant.item_code
