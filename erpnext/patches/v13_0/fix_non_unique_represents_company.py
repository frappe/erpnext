import frappe


def execute():
	frappe.db.set_value(
		"Customer",
		{"represents_company": ""},
		"represents_company",
		None,
		update_modified=False,
	)
