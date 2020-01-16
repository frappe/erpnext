# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors

from __future__ import unicode_literals
import frappe

def execute():
	hr = frappe.db.get_value("Module Def", "HR")
	if hr == "Hr":
		frappe.rename_doc("Module Def", "Hr", "HR")
		frappe.db.set_value("Module Def", "HR", "module_name", "HR")

	frappe.clear_cache()
	frappe.setup_module_map()
