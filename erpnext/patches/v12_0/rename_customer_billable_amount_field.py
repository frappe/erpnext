import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	frappe.reload_doc("projects", "doctype", "project")
	if frappe.db.has_column("Project", 'billable_amount_without_claim'):
		rename_field("Project", 'billable_amount_without_claim', 'customer_billable_amount')
