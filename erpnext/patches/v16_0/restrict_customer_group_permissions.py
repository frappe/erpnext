import frappe


def execute():
	# Custom rules can retain the previous defaults after the DocType is synced.
	frappe.db.set_value(
		"Custom DocPerm",
		{"parent": "Customer Group", "role": "Customer", "permlevel": 0, "read": 0},
		dict.fromkeys(("print", "email", "export", "report", "share"), 0),
		update_modified=False,
	)
	frappe.clear_cache(doctype="Customer Group")
