# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

def execute():
	frappe.reload_doc("manufacturing", "doctype", "bom")
	organization = frappe.db.get_value("Global Defaults", None, "default_organization")
	frappe.db.sql("""update  `tabBOM` set organization = %s""",organization)
