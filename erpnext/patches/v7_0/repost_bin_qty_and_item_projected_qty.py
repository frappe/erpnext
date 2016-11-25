# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from erpnext.stock.doctype.bin.bin import update_item_projected_qty

def execute():
	repost_bin_qty()
	repost_item_projected_qty()

def repost_bin_qty():
	for bin in frappe.db.sql(""" select name from `tabBin` 
		where (actual_qty + ordered_qty + indented_qty + planned_qty- reserved_qty - reserved_qty_for_production) != projected_qty """, as_dict=1):
		bin_doc = frappe.get_doc('Bin', bin.name)
		bin_doc.set_projected_qty()
		bin_doc.db_set("projected_qty", bin_doc.projected_qty, update_modified = False)

def repost_item_projected_qty():
	for data in frappe.db.sql(""" select 
			`tabBin`.item_code as item_code,
			sum(`tabBin`.projected_qty) as projected_qty, 
			`tabItem`.total_projected_qty as total_projected_qty 
		from 
			`tabBin`, `tabItem` 
		where `tabBin`.item_code = `tabItem`.name 
		group by `tabBin`.item_code having projected_qty <>  total_projected_qty """, as_dict=1):
		update_item_projected_qty(data.item_code)
