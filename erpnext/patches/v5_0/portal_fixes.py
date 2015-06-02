import frappe
import erpnext.setup.install

def execute():
	frappe.reload_doctype("Web Form Field")
	erpnext.setup.install.add_web_forms()
