# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
import frappe.permissions

def execute():
	frappe.reload_doc("core", "doctype", "block_module")
	frappe.reload_doctype("User")
	frappe.reload_doctype("Lead")
	frappe.reload_doctype("Contact")

	frappe.reload_doc('email', 'doctype', 'email_group')
	frappe.reload_doc('email', 'doctype', 'email_group_member')
	frappe.reload_doc('email', 'doctype', 'newsletter')

	frappe.permissions.reset_perms("Newsletter")

	if not frappe.db.exists("Role", "Newsletter Manager"):
		frappe.get_doc({"doctype": "Role", "role": "Newsletter Manager"}).insert()

	for userrole in frappe.get_all("Has Role", "parent", {"role": "Sales Manager", "parenttype": "User"}):
		if frappe.db.exists("User", userrole.parent):
			user = frappe.get_doc("User", userrole.parent)
			user.append("roles", {
				"doctype": "Has Role",
				"role": "Newsletter Manager"
			})
			user.flags.ignore_mandatory = True
			user.save()

	# create default lists
	general = frappe.new_doc("Email Group")
	general.title = "General"
	general.insert()
	general.import_from("Lead")
	general.import_from("Contact")
