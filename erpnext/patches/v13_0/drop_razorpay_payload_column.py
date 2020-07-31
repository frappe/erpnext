from __future__ import unicode_literals
import frappe

def execute():
	if frappe.db.exists("DocType", "Membership Settings"):
		if 'webhook_payload' in frappe.db.get_table_columns("Membership Settings"):
			frappe.db.sql("alter table `tabMembership Settings` drop column webhook_payload")