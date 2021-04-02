# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	for doctype in ["Purchase Order", "Purchase Invoice", "Purchase Receipt"]:
		child_table = 'Purchase Receipt Item Supplied' if doctype != 'Purchase Order' else 'Purchase Order Item Supplied'
		for data in frappe.db.sql(""" select distinct `tab{doctype}`.name from `tab{doctype}` , `tab{child_table}`
			where `tab{doctype}`.name = `tab{child_table}`.parent and `tab{doctype}`.docstatus != 2
			and `tab{doctype}`.is_subcontracted = 'No' """.format(doctype = doctype, child_table = child_table), as_dict=1):
			frappe.db.sql(""" delete from `tab{child_table}` 
				where parent = %s and parenttype = %s""".format(child_table= child_table), (data.name, doctype))