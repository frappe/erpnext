# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

def execute():
	for dt in ("Account", "Cost Center", "File", "Employee", "Land Unit", "Task", "Customer Group", "Sales Person", "Territory"):
		frappe.get_doc("DocType", dt).run_module_method("on_doctype_update")