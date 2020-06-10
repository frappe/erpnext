from __future__ import unicode_literals
import frappe

def execute():
	if frappe.db.table_exists("POS Setting"):
		frappe.rename_doc("DocType", "POS Setting", "POS Profile")
