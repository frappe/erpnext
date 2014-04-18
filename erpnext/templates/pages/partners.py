# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import frappe.website.render

def get_context(context):
	return {
		"partners": frappe.db.sql("""select * from `tabSales Partner`
			where show_in_website=1 order by name asc""", as_dict=True),
		"title": "Partners"
	}
