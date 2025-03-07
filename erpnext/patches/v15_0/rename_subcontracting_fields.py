import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	rename_field("Purchase Order Item", "sco_qty", "subcontracted_quantity")
	rename_field("Subcontracting Order Item", "sc_conversion_factor", "subcontracting_conversion_factor")
