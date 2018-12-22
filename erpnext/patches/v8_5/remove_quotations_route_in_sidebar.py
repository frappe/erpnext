# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc('website', 'doctype', 'portal_menu_item')

	frappe.db.sql("""
		delete from
			`tabPortal Menu Item`
		where
			(route = '/quotations' and title = 'Supplier Quotation')
		or (route = '/quotation' and title = 'Quotations')
	""")