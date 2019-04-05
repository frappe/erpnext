from __future__ import unicode_literals
import frappe
import erpnext.setup.install

def execute():
	frappe.reload_doc("website", "doctype", "web_form_field", force=True, reset_permissions=True)
	#erpnext.setup.install.add_web_forms()
