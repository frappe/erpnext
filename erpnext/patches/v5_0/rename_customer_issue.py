from __future__ import unicode_literals
import frappe

def execute():
	if frappe.db.table_exists("Customer Issue"):
		frappe.rename_doc("DocType", "Customer Issue", "Warranty Claim")
