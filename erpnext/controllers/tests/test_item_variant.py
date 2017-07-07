from __future__ import unicode_literals

import frappe
import json
import unittest

from erpnext.controllers.item_variant import copy_attributes_to_variant, make_variant_item_code

# python 3 compatibility stuff
try:
	unicode = unicode
except NameError:
	# Python 3
	basestring = (str, bytes)
else:
	# Python 2
	basestring = basestring


def create_variant_with_tables(item, args):
	if isinstance(args, basestring):
		args = json.loads(args)

	template = frappe.get_doc("Item", item)
	template.quality_parameters.append({
		"specification": "Moisture",
		"value": "&lt; 5%",
	})
	variant = frappe.new_doc("Item")
	variant.variant_based_on = 'Item Attribute'
	variant_attributes = []

	for d in template.attributes:
		variant_attributes.append({
			"attribute": d.attribute,
			"attribute_value": args.get(d.attribute)
		})

	variant.set("attributes", variant_attributes)
	copy_attributes_to_variant(template, variant)
	make_variant_item_code(template.item_code, template.item_name, variant)

	return variant


def make_item_variant():
	frappe.delete_doc_if_exists("Item", "_Test Variant Item-S", force=1)
	variant = create_variant_with_tables("_Test Variant Item", '{"Test Size": "Small"}')
	variant.item_code = "_Test Variant Item-S"
	variant.item_name = "_Test Variant Item-S"
	variant.save()
	return variant


class TestItemVariant(unittest.TestCase):
	def test_tables_in_template_copied_to_variant(self):
		variant = make_item_variant()
		self.assertNotEqual(variant.get("quality_parameters"), [])
