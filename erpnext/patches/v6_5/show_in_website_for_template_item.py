from __future__ import unicode_literals
import frappe
import frappe.website.render

def execute():
	for item_code in frappe.db.sql_list("""select distinct variant_of from `tabItem`
		where variant_of is not null and variant_of !='' and show_in_website=1"""):

		item = frappe.get_doc("Item", item_code)
		item.db_set("show_in_website", 1, update_modified=False)

		item.make_route()
		item.db_set("route", item.route, update_modified=False)

	frappe.website.render.clear_cache()
