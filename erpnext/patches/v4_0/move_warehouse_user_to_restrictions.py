# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import frappe.permissions

def execute():
	for warehouse, user in frappe.db.sql("""select parent, user from `tabWarehouse User`"""):
		frappe.permissions.add_user_permission("Warehouse", warehouse, user)

	frappe.delete_doc_if_exists("DocType", "Warehouse User")
	frappe.reload_doc("stock", "doctype", "warehouse")
