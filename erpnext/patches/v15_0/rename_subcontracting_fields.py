import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	if frappe.db.table_exists("Purchase Order Item") and frappe.db.has_column(
		"Purchase Order Item", "sco_qty"
	):
		rename_field("Purchase Order Item", "sco_qty", "subcontracted_quantity")

	if frappe.db.table_exists("Subcontracting Order Item") and frappe.db.has_column(
		"Subcontracting Order Item", "sc_conversion_factor"
	):
		rename_field("Subcontracting Order Item", "sc_conversion_factor", "subcontracting_conversion_factor")
