from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doctype("Project")
	
	frappe.db.sql('''
		UPDATE `tabProject`
		SET copied_from=name
		WHERE copied_from is NULL
	''')