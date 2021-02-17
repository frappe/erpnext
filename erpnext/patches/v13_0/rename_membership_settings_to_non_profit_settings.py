from __future__ import unicode_literals
import frappe

def execute():
	if frappe.db.table_exists("Membership Settings"):
		frappe.rename_doc("DocType", "Membership Settings", "Non Profit Settings")
