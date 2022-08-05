import frappe


def execute():
	doc = frappe.get_single("Domain Settings")
	doc.restrict_roles_and_modules()
