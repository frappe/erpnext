# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

def execute():
	frappe.db.sql("""update `tabBOM` as bom  set bom.item_name = \
		( select item.item_name from `tabItem` as item  where item.name = bom.item)""")
	frappe.db.sql("""update `tabBOM Item` as bomItem set bomItem.item_name = ( select item.item_name  \
		from `tabItem` as item where item.name = bomItem.item_code)""")
	frappe.db.sql("""update `tabBOM Explosion Item` as explosionItem set explosionItem.item_name = \
		( select item.item_name from `tabItem` as item where item.name = explosionItem.item_code)""")