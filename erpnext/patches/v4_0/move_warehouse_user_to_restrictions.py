# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	from frappe.core.page.user_permissions import user_permissions
	for warehouse, user in frappe.db.sql("""select parent, user from `tabWarehouse User`"""):
		user_permissions.add(user, "Warehouse", warehouse)
	
	frappe.delete_doc("DocType", "Warehouse User")
	frappe.reload_doc("stock", "doctype", "warehouse")