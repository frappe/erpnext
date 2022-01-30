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
	delete_broken_bins()
	delete_and_patch_duplicate_bins()

def delete_broken_bins():
	# delete useless bins
	frappe.db.sql("delete from `tabBin` where item_code is null or warehouse is null")

def delete_and_patch_duplicate_bins():

	duplicate_bins = frappe.db.sql("""
		SELECT
			item_code, warehouse, count(*) as bin_count
		FROM
			tabBin
		GROUP BY
			item_code, warehouse
		HAVING
			bin_count > 1
	""", as_dict=1)

	for duplicate_bin in duplicate_bins:
		existing_bins = frappe.get_list("Bin",
				filters={
					"item_code": duplicate_bin.item_code,
					"warehouse": duplicate_bin.warehouse
					},
				fields=["name"],
				order_by="creation",)

		# keep last one
		existing_bins.pop()

		for broken_bin in existing_bins:
			frappe.delete_doc("Bin", broken_bin.name)

		qty_dict = {
			"reserved_qty": get_reserved_qty(duplicate_bin.item_code, duplicate_bin.warehouse),
			"indented_qty": get_indented_qty(duplicate_bin.item_code, duplicate_bin.warehouse),
			"ordered_qty": get_ordered_qty(duplicate_bin.item_code, duplicate_bin.warehouse),
			"planned_qty": get_planned_qty(duplicate_bin.item_code, duplicate_bin.warehouse),
			"actual_qty": get_balance_qty_from_sle(duplicate_bin.item_code, duplicate_bin.warehouse)
		}

		update_bin_qty(duplicate_bin.item_code, duplicate_bin.warehouse, qty_dict)
