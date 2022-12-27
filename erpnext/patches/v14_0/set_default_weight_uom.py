import frappe


def execute():
	kg_uom = frappe.db.get_value("UOM", "Kg")
	if not kg_uom:
		kg_uom = frappe.db.get_value("UOM", "Kgs")

	if kg_uom:
		frappe.set_value("Stock Settings", None, "weight_uom", kg_uom)
