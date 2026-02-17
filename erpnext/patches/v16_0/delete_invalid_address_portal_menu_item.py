import frappe

# Ammending the incorrect route in hooks.py leaves the incorrect entry in the database, it needs to be removed manually.


def execute():
	incorrect_portal_menu_item = frappe.get_all(
		"Portal Menu Item",
		filters={
			"title": "Addresses",
			"enabled": 1,
			"route": "/addresses",
			"reference_doctype": "Address",
			"role": None,
		},
		fields=["name"],
	)

	for ipmi in incorrect_portal_menu_item:
		doc = frappe.get_doc("Portal Menu Item", ipmi.name)
		doc.delete(doc)
