# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	from frappe.core.page.user_properties import user_properties
	for warehouse, profile in frappe.db.sql("""select parent, user from `tabWarehouse User`"""):
		user_properties.add(profile, "Warehouse", warehouse)
	
	frappe.delete_doc("DocType", "Warehouse User")
	frappe.reload_doc("stock", "doctype", "warehouse")