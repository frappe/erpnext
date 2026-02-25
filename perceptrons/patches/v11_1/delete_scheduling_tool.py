# Copyright (c) 2015, Hash Include Solutions FZC and Contributors
# License: GNU General Public License v3. See license.txt


import frappe


def execute():
	if frappe.db.exists("DocType", "Scheduling Tool"):
		frappe.delete_doc("DocType", "Scheduling Tool", ignore_permissions=True)
