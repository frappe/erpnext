import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	if frappe.db.has_column("Delivery Stop", "lock"):
		rename_field("Delivery Stop", "lock", "locked")
