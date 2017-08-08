# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doctype("POS Profile")
	frappe.reload_doctype("Sales Invoice Payment")

	frappe.db.sql("""
		update
			`tabSales Invoice Payment`
		set `tabSales Invoice Payment`.default = 1
		where
			`tabSales Invoice Payment`.parenttype = 'POS Profile'
			and `tabSales Invoice Payment`.idx=1""")