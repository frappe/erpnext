import frappe


def execute():
	frappe.reload_doctype("Payment Entry")
	frappe.db.set_value("Payment Entry", {"docstatus": 1}, "status", "Submitted", update_modified=False)
	frappe.db.set_value("Payment Entry", {"docstatus": 2}, "status", "Cancelled", update_modified=False)
	frappe.db.set_value("Payment Entry", {"docstatus": 0}, "status", "Draft", update_modified=False)
