import frappe


def execute():
	frappe.reload_doc("stock", "doctype", "shipment")

	# update submitted status
	frappe.db.set_value(
		"Shipment",
		{"status": "Draft", "docstatus": 1},
		"status",
		"Submitted",
		update_modified=False,
	)

	# update cancelled status
	frappe.db.set_value(
		"Shipment",
		{"status": "Draft", "docstatus": 2},
		"status",
		"Cancelled",
		update_modified=False,
	)
