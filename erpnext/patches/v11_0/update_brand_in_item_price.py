# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

def execute():
	frappe.reload_doc('stock', 'doctype', 'item_price')

	frappe.db.sql(""" update `tabItem Price`, `tabItem`
		set
			`tabItem Price`.brand = `tabItem`.brand
		where
			`tabItem Price`.item_code = `tabItem`.name 
			and `tabItem`.brand is not null and `tabItem`.brand != ''""")