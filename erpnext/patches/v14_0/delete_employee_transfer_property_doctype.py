import frappe


def execute():
	frappe.delete_doc("DocType", "Employee Transfer Property", ignore_missing=True)
