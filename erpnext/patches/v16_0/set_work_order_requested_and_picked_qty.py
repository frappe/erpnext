import frappe


def execute():
	"""Backfill requested_qty and picked_qty for work orders with open demand;
	fulfilled documents leave the zero default."""
	work_orders = set(
		frappe.get_all(
			"Material Request",
			filters={
				"docstatus": 1,
				"material_request_type": "Material Transfer",
				"work_order": ("is", "set"),
				"status": ("!=", "Stopped"),
				"per_ordered": ("<", 100),
			},
			pluck="work_order",
			distinct=True,
		)
	)
	work_orders.update(
		frappe.get_all(
			"Pick List",
			filters={"docstatus": 1, "work_order": ("is", "set"), "status": ("!=", "Completed")},
			pluck="work_order",
			distinct=True,
		)
	)

	for name in work_orders:
		if frappe.db.get_value("Work Order", name, "docstatus") != 1:
			continue

		work_order = frappe.get_doc("Work Order", name)
		work_order.update_requested_qty_for_required_items()
		work_order.update_picked_qty_for_required_items()
