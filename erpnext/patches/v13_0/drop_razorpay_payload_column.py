from __future__ import unicode_literals
import frappe

def execute():
	if frappe.db.exists("DocType", "Membership"):
		if 'webhook_payload' in frappe.db.get_table_columns("Membership"):
			frappe.db.sql("alter table `tabMembership` drop column webhook_payload")