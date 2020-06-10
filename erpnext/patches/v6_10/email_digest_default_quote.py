from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doctype("Email Digest")
	frappe.db.sql("update `tabEmail Digest` set add_quote = 1")
