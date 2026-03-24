import frappe


def execute():
	frappe.reload_doc("manufacturing", "doctype", "workstation")

	frappe.db.set_value("Workstation", {}, "production_capacity", 1, update_modified=False)
