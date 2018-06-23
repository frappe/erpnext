# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	repost_bin_qty()

def repost_bin_qty():
	for bin in frappe.db.sql(""" select name from `tabBin`
		where (actual_qty + ordered_qty + indented_qty + planned_qty- reserved_qty - reserved_qty_for_production) != projected_qty """, as_dict=1):
		bin_doc = frappe.get_doc('Bin', bin.name)
		bin_doc.set_projected_qty()
		bin_doc.db_set("projected_qty", bin_doc.projected_qty, update_modified = False)
