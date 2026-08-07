import frappe

from erpnext.manufacturing.doctype.work_order.services.required_items import RequiredItemsService


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

		service = RequiredItemsService(frappe.get_doc("Work Order", name))
		service.update_requested_qty_for_required_items()
		service.update_picked_qty_for_required_items()
