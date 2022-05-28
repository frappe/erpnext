import frappe


def execute():
	if frappe.db.count("Asset") and frappe.db.has_column("Asset", "asset_quantity"):
		frappe.reload_doc("assets", "doctype", "Asset")
		asset = frappe.qb.DocType("Asset")
		frappe.qb.update(asset).set(asset.asset_quantity, 1).run()
