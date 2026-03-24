import frappe


def execute():
	frappe.reload_doc("accounts", "doctype", "pos_closing_entry")
	frappe.db.set_value("POS Closing Entry", {"status": "Queued"}, "status", "Failed", update_modified=False)
