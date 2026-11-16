import frappe

from erpnext.stock.doctype.material_request.material_request import (
	update_plan_item_requested_qty,
	update_production_plan_status,
)
from erpnext.stock.get_item_details import get_conversion_factor


def execute():
	"""Plan rows saved before #60628 hold a stock UOM qty under the purchase UOM at conversion factor 1."""
	rows = get_plan_rows_in_other_uom_at_conversion_factor_one()
	conversion_factors = {
		(item_code, uom): get_conversion_factor(item_code, uom)["conversion_factor"]
		for item_code, uom in {(row.item_code, row.uom) for row in rows}
	}
	rows = [row for row in rows if conversion_factors[(row.item_code, row.uom)] != 1]
	frappe.db.bulk_update(
		"Material Request Plan Item",
		{row.name: {"uom": row.stock_uom} for row in rows},
		update_modified=False,
	)

	# requested_qty of these rows was counted in the Material Request UOM
	names = [row.name for row in rows]
	for start in range(0, len(names), 500):
		update_plan_item_requested_qty(names[start : start + 500])
	update_production_plan_status({row.parent for row in rows if row.docstatus == 1})


def get_plan_rows_in_other_uom_at_conversion_factor_one():
	plan_item = frappe.qb.DocType("Material Request Plan Item")
	item = frappe.qb.DocType("Item")

	return (
		frappe.qb.from_(plan_item)
		.join(item)
		.on(item.name == plan_item.item_code)
		.select(
			plan_item.name,
			plan_item.parent,
			plan_item.docstatus,
			plan_item.item_code,
			plan_item.uom,
			item.stock_uom,
		)
		.where((plan_item.conversion_factor == 1) & (plan_item.uom != item.stock_uom))
	).run(as_dict=True)
