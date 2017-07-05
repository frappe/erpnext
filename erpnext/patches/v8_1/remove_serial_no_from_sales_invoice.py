# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc('stock', 'doctype', 'serial_no')

	frappe.db.sql("""
		update
			`tabSerial No`
		set
			sales_invoice= NULL
		where
			sales_invoice is not null and sales_invoice !='' and
			sales_invoice in(select name from `tabSales Invoice` where update_stock = 0) """)