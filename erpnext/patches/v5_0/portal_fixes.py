import frappe
import erpnext.setup.install

def execute():
	frappe.reload_doc("website", "doctype", "web_form_field", force=True)
	erpnext.setup.install.add_web_forms()
