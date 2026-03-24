import frappe


def execute():
	options = {
		"11-20": "11-50",
		"21-30": "11-50",
		"31-100": "51-200",
		"101-500": "201-500",
		"500-1000": "501-1000",
		">1000": "1000+",
	}

	for doctype in ("Lead", "Opportunity", "Prospect"):
		frappe.reload_doctype(doctype)
		for key, value in options.items():
			frappe.db.set_value(
				doctype,
				{"no_of_employees": key},
				"no_of_employees",
				value,
				update_modified=False,
			)
