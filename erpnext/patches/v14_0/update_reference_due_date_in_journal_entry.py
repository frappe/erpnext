import frappe


def execute():
	if frappe.db.get_value("Journal Entry Account", {"reference_due_date": ""}):
		frappe.db.set_value(
			"Journal Entry Account",
			{"reference_due_date": ""},
			"reference_due_date",
			None,
			update_modified=False,
		)
