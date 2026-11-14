import frappe


def execute():
	"""Plan rows saved before #60628 hold a stock UOM qty under the purchase UOM at conversion factor 1."""
	rows = get_plan_rows_with_stock_qty_in_other_uom()
	frappe.db.bulk_update(
		"Material Request Plan Item",
		{row.name: {"uom": row.stock_uom} for row in rows},
		update_modified=False,
	)


def get_plan_rows_with_stock_qty_in_other_uom():
	plan_item = frappe.qb.DocType("Material Request Plan Item")
	item = frappe.qb.DocType("Item")
	uom_conversion = frappe.qb.DocType("UOM Conversion Detail")

	return (
		frappe.qb.from_(plan_item)
		.join(item)
		.on(item.name == plan_item.item_code)
		.join(uom_conversion)
		.on(
			(uom_conversion.parenttype == "Item")
			& (uom_conversion.parent == plan_item.item_code)
			& (uom_conversion.uom == plan_item.uom)
		)
		.select(plan_item.name, item.stock_uom)
		.where(
			(plan_item.conversion_factor == 1)
			& (plan_item.uom != item.stock_uom)
			& (uom_conversion.conversion_factor != 1)
		)
	).run(as_dict=True)
