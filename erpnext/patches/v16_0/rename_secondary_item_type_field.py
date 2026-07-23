import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	doctypes = [
		"BOM Secondary Item",
		"Job Card Secondary Item",
		"Stock Entry Detail",
		"Subcontracting Inward Order Secondary Item",
		"Subcontracting Receipt Item",
	]

	for doctype in doctypes:
		if not frappe.db.has_column(doctype, "type"):
			continue

		rename_field(doctype, "type", "secondary_item_type")
