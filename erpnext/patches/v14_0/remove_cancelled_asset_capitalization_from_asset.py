import frappe


def execute():
	cancelled_asset_capitalizations = frappe.get_all(
		"Asset Capitalization",
		filters={"docstatus": 2},
		fields=["name", "target_asset"],
	)
	for asset_capitalization in cancelled_asset_capitalizations:
		frappe.db.set_value("Asset", asset_capitalization.target_asset, "capitalized_in", None)
