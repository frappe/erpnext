import frappe


def execute():
	frappe.reload_doc("projects", "doctype", "projects_settings")
	frappe.db.set_value("Projects Settings", None, "remove_assignment_on_task_completion", True)