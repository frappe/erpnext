# Copyright (c) 2020, Frappe and Contributors
# License: GNU General Public License v3. See license.txt


import frappe


def execute():
	if frappe.db.exists("DocType", "Issue"):
		frappe.reload_doc("support", "doctype", "issue")
		rename_status()


def rename_status():
	frappe.db.set_value("Issue", {"status": "Hold"}, "status", "On Hold", update_modified=False)
