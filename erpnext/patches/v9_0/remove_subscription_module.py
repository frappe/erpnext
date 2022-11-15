# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

def execute():
	if frappe.db.exists('Module Def', 'Subscription'):
		frappe.db.sql(""" delete from `tabModule Def` where name = 'Subscription'""")