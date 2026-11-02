import frappe


def execute():
	frappe.db.set_value(
		"Stock Entry Type",
		{"is_standard": 1, "add_to_transit": 1},
		"add_to_transit",
		0,
		update_modified=False,
	)
