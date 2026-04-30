import frappe


def execute():
	if frappe.db.exists("Portal Menu Item", {"route": "/addresses", "reference_doctype": "Address"}) and (
		doc := frappe.get_doc("Portal Menu Item", {"route": "/addresses", "reference_doctype": "Address"})
	):
		doc.role = "Customer"
		doc.save()

	website_settings = frappe.get_single("Website Settings")
	website_settings.append("route_redirects", {"source": "addresses", "target": "address/list"})
	website_settings.append("route_redirects", {"source": "projects", "target": "project"})
	website_settings.save()
