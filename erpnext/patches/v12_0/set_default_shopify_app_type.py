import frappe


def execute():
	frappe.reload_doc("erpnext_integrations", "doctype", "shopify_settings")
	frappe.db.set_value("Shopify Settings", None, "app_type", "Private")
