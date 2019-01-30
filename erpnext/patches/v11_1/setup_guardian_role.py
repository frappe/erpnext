from __future__ import unicode_literals
import frappe

def execute():
	if 'Education' in frappe.get_active_domains() and not frappe.db.exists("Role", "Guardian"):
		frappe.new_doc({
			"doctype": "Role",
			"role_name": "Guardian",
			"desk_access": 0
		}).insert(ignore_permissions=True)
