# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

def execute():
	frappe.db.sql("""update `tabBOM` set `tabBOM`.item_name = ( select `tabItem`.item_name \
		from `tabItem` where `tabItem`.name = `tabBOM`.item)""")
	frappe.db.sql("""update `tabBOM Item` set item_name = ( select item_name  \
		from tabItem where `tabItem`.name = `tabBOM Item`.item_code)""")
	frappe.db.sql("""update `tabBOM Explosion Item` set `tabBOM Explosion Item`.item_name = \
		( select `tabItem`.item_name from `tabItem` where `tabItem`.name = `tabBOM Explosion Item`.item_code)""")