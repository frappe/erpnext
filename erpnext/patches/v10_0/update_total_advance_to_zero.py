# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	for doctype in ['Purchase Order', 'Sales Order']:
		for d in frappe.db.sql(""" select name, advance_paid from `tab%s`
			where advance_paid > 0 and docstatus = 1""" % (doctype), as_dict=1):
			frappe.get_doc(doctype, d.name).set_total_advance_paid()