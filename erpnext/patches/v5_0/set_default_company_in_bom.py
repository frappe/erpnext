# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc("manufacturing", "doctype", "bom")
	company = frappe.db.get_value("Global Defaults", None, "default_company")
	frappe.db.sql("""update  `tabBOM` set company = %s""",company)
