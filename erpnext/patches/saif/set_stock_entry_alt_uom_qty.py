# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

def execute():
	frappe.reload_doc('stock', 'doctype', 'stock_entry_detail')

	frappe.db.sql("""
		update tabItem
		set alt_uom_size = 1
		where ifnull(alt_uom, '') = ''
	""")

	frappe.db.sql("""
		update `tabStock Entry Detail` d
		inner join tabItem i on i.name = d.item_code
		set
			d.alt_uom = i.alt_uom,
			d.alt_uom_size = i.alt_uom_size,
			d.alt_uom_qty = d.transfer_qty * i.alt_uom_size
	""")
