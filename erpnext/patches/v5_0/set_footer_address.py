import frappe

def execute():
	ss = frappe.get_doc("System Settings", "System Settings")
	ss.email_footer_address = frappe.db.get_default("company")
	ss.save()
