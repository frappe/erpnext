# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe


def execute():
	if not frappe.db.table_exists("tabBlanket Order Item"):
		return

	items = frappe.get_all(
		"Blanket Order Item",
		filters={"uom": ("is", "not set")},
		fields=["name", "item_code", "qty"],
	)

	for row in items:
		stock_uom = frappe.db.get_value("Item", row.item_code, "stock_uom")
		if not stock_uom:
			continue

		frappe.db.set_value(
			"Blanket Order Item",
			row.name,
			{
				"uom": stock_uom,
				"stock_uom": stock_uom,
				"conversion_factor": 1,
				"stock_qty": row.qty or 0,
			},
			update_modified=False,
		)
