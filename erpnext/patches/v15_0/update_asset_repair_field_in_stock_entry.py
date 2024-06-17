import frappe


def execute():
	if frappe.db.has_column("Asset Repair", "stock_entry"):
		asset_repairs = frappe.get_all("Asset Repair", fields=["name", "stock_entry"])

		for asset_repair in asset_repairs:
			if asset_repair.stock_entry:
				frappe.db.set_value(
					"Stock Entry", asset_repair.stock_entry, "asset_repair", asset_repair.name
				)
		frappe.db.commit()
