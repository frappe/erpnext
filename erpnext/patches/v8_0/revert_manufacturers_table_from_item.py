# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	if frappe.db.exists("DocType", "Item Manufacturer"):
		frappe.reload_doctype("Item")
		item_manufacturers = frappe.db.sql("""
			select parent, manufacturer, manufacturer_part_no 
			from `tabItem Manufacturer`
		""", as_dict=1)
		
		for im in item_manufacturers:
			frappe.db.sql("""
				update tabItem 
				set manufacturer=%s, manufacturer_part_no=%s
				where name=%s
			""", (im.manufacturer, im.manufacturer_part_no, im.parent))
		
		frappe.delete_doc("DocType", "Item Manufacturer")