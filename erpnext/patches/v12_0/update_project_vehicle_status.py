import frappe


def execute():
	frappe.reload_doc("projects", "doctype", "project")
	docs = frappe.get_all("Project")
	for d in docs:
		doc = frappe.get_doc("Project", d.name)
		doc.set_vehicle_status(update=True, update_modified=False)
		doc.clear_cache()
