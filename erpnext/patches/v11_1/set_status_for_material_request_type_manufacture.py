import frappe


def execute():
	frappe.db.set_value(
		"Material Request",
		{
			"docstatus": 1,
			"material_request_type": "Manufacture",
			"per_ordered": 100,
			"status": ["!=", "Stopped"],
		},
		"status",
		"Manufactured",
		update_modified=False,
	)
