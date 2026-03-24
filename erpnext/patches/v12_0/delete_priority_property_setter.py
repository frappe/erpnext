import frappe


def execute():
	frappe.db.delete(
		"Property Setter",
		{"doc_type": "Issue", "field_name": "priority", "property": "options"},
	)
