import frappe
from frappe.permissions import add_permission, update_permission_property
from frappe.core.page.permission_manager.permission_manager import remove

def execute():
	frappe.reload_doc("projects", "doctype", "project")

	add_permission("Project", "Projects Manager", 1)
	update_permission_property("Project", "Projects Manager", 1, "write", 1)
	remove("Project", "All", 1)
