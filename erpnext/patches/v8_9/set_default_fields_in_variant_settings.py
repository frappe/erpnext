# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc('stock', 'doctype', 'item_variant_settings')
	frappe.reload_doc('stock', 'doctype', 'variant_field')

	doc = frappe.get_doc('Item Variant Settings')
	doc.set_default_fields()
	doc.save()