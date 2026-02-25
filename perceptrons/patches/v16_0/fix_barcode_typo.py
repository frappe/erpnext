import frappe


def execute():
	frappe.qb.update("Item Barcode").set("barcode_type", "EAN-13").where(
		frappe.qb.Field("barcode_type") == "EAN-12"
	).run()
