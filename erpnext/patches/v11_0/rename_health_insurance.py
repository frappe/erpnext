# Copyright (c) 2018, Frappe and Contributors
# License: GNU General Public License v3. See license.txt


import frappe


def execute():
	frappe.rename_doc("DocType", "Health Insurance", "Employee Health Insurance", force=True)
	frappe.reload_doc("hr", "doctype", "employee_health_insurance")
