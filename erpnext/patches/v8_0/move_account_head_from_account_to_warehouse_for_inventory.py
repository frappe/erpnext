# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

def execute():
	frappe.reload_doctype("Warehouse")
	frappe.db.sql("""
		update 
			`tabWarehouse` 
		set 
			account = (select name from `tabAccount` 
				where account_type = 'Stock' and 
				warehouse = `tabWarehouse`.name and is_group = 0 limit 1)""")