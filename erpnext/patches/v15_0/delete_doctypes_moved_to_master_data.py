import frappe


def execute():
	doctypes = ["Supplier"]
	for doctype in doctypes:
		frappe.delete_doc("DocType", doctype, ignore_missing=True)
