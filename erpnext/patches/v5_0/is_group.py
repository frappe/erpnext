from __future__ import unicode_literals

import frappe

def execute():
	frappe.reload_doctype("Account")
	frappe.reload_doctype("Cost Center")
	frappe.db.sql("update tabAccount set is_group = if(group_or_ledger='Group', 1, 0)")
	frappe.db.sql("update `tabCost Center` set is_group = if(group_or_ledger='Group', 1, 0)")
