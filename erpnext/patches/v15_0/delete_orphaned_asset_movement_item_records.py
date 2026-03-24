import frappe


def execute():
	asset_movement = frappe.qb.DocType("Asset Movement")
	asset_movement_item = frappe.qb.DocType("Asset Movement Item")
	valid_parents = frappe.qb.from_(asset_movement).select(asset_movement.name)

	frappe.qb.from_(asset_movement_item).delete().where(asset_movement_item.parent.notin(valid_parents)).run()
