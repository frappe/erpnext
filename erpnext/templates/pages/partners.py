# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import frappe.website.render

page_title = "Partners"

def get_context(context):
	partners = frappe.db.sql("""select * from `tabSales Partner`
			where show_in_website=1 order by name asc""", as_dict=True)

	for p in partners:
		p.route = frappe.get_doc("Sales Partner", p.name).get_route()

	return {
		"partners": partners,
		"title": page_title
	}
