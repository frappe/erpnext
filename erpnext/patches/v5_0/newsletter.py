# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
import frappe.permisssions

def execute():
	frappe.reload_doctype("User")
	frappe.reload_doctype("Lead")
	frappe.reload_doctype("Contact")

	frappe.reload_doc('crm', 'doctype', 'newsletter_list')
	frappe.reload_doc('crm', 'doctype', 'newsletter_list_subscriber')
	frappe.reload_doc('crm', 'doctype', 'newsletter')

	frappe.permisssions.reset_perms("Newsletter")

	if not frappe.db.exists("Role", "Newsletter Manager"):
		frappe.get_doc({"doctype": "Role", "role": "Newsletter Manager"}).insert()

	for userrole in frappe.get_all("UserRole", "parent", {"role": "Sales Manager"}):
		user = frappe.get_doc("User", userrole.parent)
		user.add_roles("Newsletter Manager")

	# create default lists
	general = frappe.new_doc("Newsletter List")
	general.title = "General"
	general.insert()
	general.import_from("Lead")
	general.import_from("Contact")
