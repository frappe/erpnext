import frappe


def execute():
	frappe.reload_doc("projects", "doctype", "project")

	for d in frappe.get_all("Project"):
		doc = frappe.get_doc("Project", d.name)
		doc.set_project_date()
		doc.db_set('project_date', doc.project_date, update_modified=False)
		doc.clear_cache()
