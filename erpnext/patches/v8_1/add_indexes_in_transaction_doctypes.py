# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	for dt in ("Sales Order Item", "Purchase Order Item",
		"Material Request Item", "Work Order Item", "Packed Item"):
			frappe.get_doc("DocType", dt).run_module_method("on_doctype_update")