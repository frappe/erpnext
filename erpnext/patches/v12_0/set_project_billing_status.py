import frappe


def execute():
	frappe.reload_doc("projects", "doctype", "project_status")
	frappe.reload_doc("projects", "doctype", "project")

	projects = frappe.get_all("Project")
	for d in projects:
		doc = frappe.get_doc("Project", d.name)
		doc.set_billing_status(update=True, update_modified=False)
		doc.clear_cache()
