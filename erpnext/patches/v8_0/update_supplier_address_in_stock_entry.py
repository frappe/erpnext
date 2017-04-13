# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	# copy supplier_address to address_display, and set supplier_address to blank

	stock_entries = frappe.db.sql(""" select name, purchase_order, supplier_address from `tabStock Entry`
		where ifnull(supplier_address, '') <> ''""", as_dict=True)

	frappe.reload_doc('stock', 'doctype', 'stock_entry')

	for stock_entry in stock_entries:
		# move supplier address to address_display, and fetch the supplier address from purchase order

		se = frappe.get_doc("Stock Entry", stock_entry.get("name"))
		se.address_display = stock_entry.get("supplier_address")
		se.supplier_address = frappe.db.get_value("Purchase Order", stock_entry.get("purchase_order"),"supplier_address") or None

		se.db_update()
