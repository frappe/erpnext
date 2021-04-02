from __future__ import unicode_literals
import frappe

def execute():
	default_warehouse = frappe.db.get_value("Stock Settings", None, "default_warehouse")
	if default_warehouse:
		if not frappe.db.get_value("Warehouse", {"name": default_warehouse}):
			frappe.db.set_value("Stock Settings", None, "default_warehouse", "")