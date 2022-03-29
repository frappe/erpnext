import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	frappe.reload_doc("Healthcare", "doctype", "Inpatient Record")
	if frappe.db.has_column("Inpatient Record", "discharge_ordered_date"):
		rename_field("Inpatient Record", "discharge_ordered_date", "discharge_ordered_datetime")
