# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

def execute():
	for dt in ("Stock Ledger Entry", "Communication", "DefaultValue", "DocShare", "File", "ToDo"):
		frappe.get_doc("DocType", dt).run_module_method("on_doctype_update")
