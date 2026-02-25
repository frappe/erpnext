import frappe


def execute():
	AssetValueAdjustment = frappe.qb.DocType("Asset Value Adjustment")

	frappe.qb.update(AssetValueAdjustment).set(
		AssetValueAdjustment.difference_amount,
		AssetValueAdjustment.new_asset_value - AssetValueAdjustment.current_asset_value,
	).where(AssetValueAdjustment.docstatus != 2).run()
