import frappe

from erpnext.stock.stock_balance import (
	get_balance_qty_from_sle,
	get_indented_qty,
	get_ordered_qty,
	get_planned_qty,
	get_reserved_qty,
	update_bin_qty,
)


def execute():

	duplicate_rows = frappe.db.sql("""
		SELECT
		item_code, warehouse
		FROM
			tabBin
		GROUP BY
			item_code, warehouse
		HAVING
			COUNT(*) > 1
	""", as_dict=1)

	for row in duplicate_rows:
		bins = frappe.get_list("Bin",
							   filters={"item_code": row.item_code,
										"warehouse": row.warehouse},
							   fields=["name"],
							   order_by="creation",
							   )

		for x in range(len(bins) - 1):
			frappe.delete_doc("Bin", bins[x].name)

		qty_dict = {
			"reserved_qty": get_reserved_qty(row.item_code, row.warehouse),
			"indented_qty": get_indented_qty(row.item_code, row.warehouse),
			"ordered_qty": get_ordered_qty(row.item_code, row.warehouse),
			"planned_qty": get_planned_qty(row.item_code, row.warehouse),
			"actual_qty": get_balance_qty_from_sle(row.item_code, row.warehouse)
		}

		update_bin_qty(row.item_code, row.warehouse, qty_dict)
