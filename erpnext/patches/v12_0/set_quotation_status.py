import frappe


def execute():
	frappe.db.set_value(
		"Quotation",
		{"docstatus": 1, "status": "Submitted"},
		"status",
		"Open",
		update_modified=False,
	)
