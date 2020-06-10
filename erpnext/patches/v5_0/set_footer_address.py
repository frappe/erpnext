from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doctype("System Settings")
	ss = frappe.get_doc("System Settings", "System Settings")
	ss.email_footer_address = frappe.db.get_default("company")
	ss.flags.ignore_mandatory = True
	ss.save()
