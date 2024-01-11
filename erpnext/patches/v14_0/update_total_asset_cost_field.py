import frappe


def execute():
	asset = frappe.qb.DocType("Asset")
	frappe.qb.update(asset).set(asset.total_asset_cost, asset.gross_purchase_amount).run()

	asset_repair_list = frappe.db.get_all(
		"Asset Repair",
		filters={"docstatus": 1, "repair_status": "Completed", "capitalize_repair_cost": 1},
		fields=["asset", "repair_cost"],
	)

	for asset_repair in asset_repair_list:
		frappe.qb.update(asset).set(
			asset.total_asset_cost, asset.total_asset_cost + asset_repair.repair_cost
		).where(asset.name == asset_repair.asset).run()
