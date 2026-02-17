import frappe


def execute():
	"""
	Amending the incorrect route in hooks.py leaves
	the incorrect entry to /addresses in the database
	and in the Portal Settings which needs to be
	removed manually.

	This patch deletes the incorrect entry so that
	only the correct entry with route /address
	remains in the database and Portal Settings.
	"""

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
		frappe.delete_doc("Portal Menu Item", ipmi.name, force=True)
