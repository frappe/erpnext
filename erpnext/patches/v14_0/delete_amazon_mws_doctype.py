import frappe


def execute():
	frappe.delete_doc("DocType", "Amazon MWS Settings", ignore_missing=True)
