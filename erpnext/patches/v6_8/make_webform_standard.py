import frappe

def execute():
	frappe.reload_doctype("Web Form")
	frappe.delete_doc("Web Form", "Issues")
	frappe.delete_doc("Web Form", "Addresses")

	from erpnext.setup.install import add_web_forms
	add_web_forms()
