import frappe

def execute():
	frappe.reload_doctype('Employee')
	frappe.db.sql('update tabEmployee set first_name = employee_name')