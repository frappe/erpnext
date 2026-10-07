import frappe


def execute():
	item_codes = set(
		frappe.get_all("Blanket Order Item", filters={"stock_uom": ("is", "not set")}, pluck="item_code")
	)
	for item_code in item_codes:
		stock_uom = frappe.get_cached_value("Item", item_code, "stock_uom")
		frappe.db.set_value(
			"Blanket Order Item", {"item_code": item_code}, "stock_uom", stock_uom, update_modified=False
		)
