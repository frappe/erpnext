import frappe

def execute():
	frappe.delete_doc("DocType", "Process Payroll")
