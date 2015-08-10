# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	item_attribute = {}
	for d in  frappe.db.sql("""select DISTINCT va.attribute, i.variant_of from `tabVariant Attribute` va, `tabItem` i \
		where va.parent = i.name""", as_dict=1):
		item_attribute.setdefault(d.variant_of, []).append({"attribute": d.attribute})
	
	for item, attributes in item_attribute.items():
		template = frappe.get_doc("Item", item)
		template.set('attributes', attributes)
		template.save()
		
	frappe.delete_doc("DocType", "Manage Variants")
	frappe.delete_doc("DocType", "Manage Variants Item")