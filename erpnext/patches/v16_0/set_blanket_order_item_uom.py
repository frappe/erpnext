# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe


def execute():
	if not frappe.db.table_exists("Blanket Order Item"):
		return

	blanket_order_item = frappe.qb.DocType("Blanket Order Item")
	(
		frappe.qb.update(blanket_order_item)
		.set(blanket_order_item.uom, blanket_order_item.stock_uom)
		.set(blanket_order_item.conversion_factor, 1)
		.set(blanket_order_item.stock_qty, blanket_order_item.qty)
		.set(blanket_order_item.stock_uom_rate, blanket_order_item.rate)
		.where((blanket_order_item.uom.isnull()) | (blanket_order_item.uom == ""))
		.where(blanket_order_item.stock_uom.isnotnull() & (blanket_order_item.stock_uom != ""))
	).run()

	missing_uom = frappe.get_all(
		"Blanket Order Item",
		filters={"uom": ("is", "not set")},
		fields=["name", "item_code", "qty", "rate"],
	)
	if not missing_uom:
		return

	stock_uoms = dict(
		frappe.get_all(
			"Item",
			filters={"name": ("in", [row.item_code for row in missing_uom])},
			fields=["name", "stock_uom"],
			as_list=True,
		)
	)
	for row in missing_uom:
		stock_uom = stock_uoms.get(row.item_code)
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
				"stock_uom_rate": row.rate or 0,
			},
			update_modified=False,
		)
