import frappe


def execute():
	frappe.db.set_value(
		"POS Profile",
		{"print_format": "Point of Sale"},
		"print_format",
		"POS Invoice",
		update_modified=False,
	)
