import frappe
from frappe import _

def execute():
	frappe.reload_doctype("System Settings")
	settings = frappe.get_doc("System Settings")
	settings.db_set("app_name", "ERPNext", commit=True)
