import frappe


def execute():
	plans = frappe.get_all(
		"Production Plan",
		filters={"docstatus": 1, "status": ("not in", ["Completed", "Closed"])},
		pluck="name",
	)
	if not plans:
		return

	rows = frappe.get_all(
		"Material Request Plan Item",
		filters={"parent": ("in", plans)},
		fields=["item_code", "warehouse"],
	)

	for item_code, warehouse in {(row.item_code, row.warehouse) for row in rows}:
		bin_name = frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse})
		if not bin_name:
			continue
		frappe.get_doc("Bin", bin_name, for_update=True).update_reserved_qty_for_production_plan()
