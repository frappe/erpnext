import frappe


def execute():
	frappe.delete_doc("DocType", "Woocommerce Settings", ignore_missing=True)
