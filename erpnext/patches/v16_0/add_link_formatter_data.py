import frappe

LINK_FIELD_DATA = [
	{"doctype_name": "Item", "link_fieldname": "item_code", "display_fieldname": "item_name"},
	{"doctype_name": "Employee", "link_fieldname": "employee", "display_fieldname": "employee_name"},
	{"doctype_name": "Project", "link_fieldname": "project", "display_fieldname": "project_name"},
]


def execute():
	link_formatter = frappe.get_single("Link Formatter")

	for data in LINK_FIELD_DATA:
		exists = any(
			row.doctype_name == data["doctype_name"] and row.link_fieldname == data["link_fieldname"]
			for row in link_formatter.link_field_display
		)

		if not exists:
			link_formatter.append("link_field_display", data)

	link_formatter.save()
