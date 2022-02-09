import frappe


def execute():
	frappe.delete_doc("DocType", "Shopify Settings", ignore_missing=True)
	frappe.delete_doc("DocType", "Shopify Log", ignore_missing=True)
