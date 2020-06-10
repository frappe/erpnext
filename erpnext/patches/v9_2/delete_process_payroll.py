from __future__ import unicode_literals
import frappe

def execute():
	frappe.delete_doc("DocType", "Process Payroll")
