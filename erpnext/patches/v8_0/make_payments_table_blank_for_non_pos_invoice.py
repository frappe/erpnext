# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doctype('Sales Invoice')

	frappe.db.sql("""
		delete from 
			`tabSales Invoice Payment` 
		where 
			parent in (select name from `tabSales Invoice` where is_pos = 0)
	""")