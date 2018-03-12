# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doctype('Material Request')
	frappe.reload_doctype('Material Request Item')

	frappe.db.sql(""" update `tabMaterial Request Item`
		set stock_uom = uom, stock_qty = qty, conversion_factor = 1.0""")