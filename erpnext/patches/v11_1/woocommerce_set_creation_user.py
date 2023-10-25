import frappe
from frappe.utils import cint


def execute():
	frappe.reload_doc("erpnext_integrations", "doctype", "woocommerce_settings")
	doc = frappe.get_doc("Woocommerce Settings")

	if cint(doc.enable_sync):
		doc.creation_user = doc.modified_by
		doc.save(ignore_permissions=True)
