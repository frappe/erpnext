import frappe


def execute():
	frappe.reload_doc("maintenance", "doctype", "Maintenance Schedule Detail")
	frappe.db.set_value(
		"Maintenance Schedule Detail",
		{"docstatus": ["<", 2]},
		"completion_status",
		"Pending",
		update_modified=False,
	)
