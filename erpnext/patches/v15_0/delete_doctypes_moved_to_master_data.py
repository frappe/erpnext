import frappe


def execute():
	doctypes = ["Supplier", "Activity Type"]
	for doctype in doctypes:
		frappe.delete_doc("DocType", doctype, ignore_missing=True)
