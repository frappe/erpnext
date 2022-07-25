import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	if frappe.db.table_exists("Vehicle Workshop"):
		frappe.rename_doc('DocType', 'Vehicle Workshop', 'Project Workshop', force=True)

	frappe.reload_doc("projects", "doctype", "project_workshop")

	if frappe.db.has_column("Project Workshop", "vehicle_workshop_name"):
		rename_field("Project Workshop", "vehicle_workshop_name", "workshop_name")

	frappe.delete_doc_if_exists("DocType", "Vehicle Workshop")
	frappe.delete_doc_if_exists("Custom Field", "Project-vehicle_workshop")

	if frappe.db.has_column("Vehicle Service Receipt", "vehicle_workshop"):
		rename_field("Vehicle Service Receipt", "vehicle_workshop", "project_workshop")
	if frappe.db.has_column("Vehicle Gate Pass", "vehicle_workshop"):
		rename_field("Vehicle Gate Pass", "vehicle_workshop", "project_workshop")
	if frappe.db.has_column("Project", "vehicle_workshop"):
		rename_field("Project", "vehicle_workshop", "project_workshop")
