import frappe
from frappe.utils import flt
from pypika import functions as fn

from erpnext.manufacturing.doctype.work_order.services.material_coverage import (
	get_minimum_material_coverage_fraction,
)


def execute():
	updates = get_precision_affected_work_orders()
	frappe.db.bulk_update("Work Order", updates, update_modified=False)


def get_precision_affected_work_orders():
	"""Return Work Orders whose components cover the plan at quantity precision."""
	work_orders = {}
	for row in _get_candidate_rows():
		work_order = work_orders.setdefault(
			row.work_order,
			{"qty": flt(row.qty), "required_qty": {}, "transferred_qty": {}},
		)
		item_code = row.item_code
		work_order["required_qty"][item_code] = work_order["required_qty"].get(item_code, 0.0) + flt(
			row.required_qty
		)
		work_order["transferred_qty"][item_code] = max(
			work_order["transferred_qty"].get(item_code, 0.0), flt(row.transferred_qty)
		)

	precision = frappe.get_precision("Work Order Item", "required_qty")
	return {
		name: {"material_transferred_for_manufacturing": values["qty"]}
		for name, values in work_orders.items()
		if get_minimum_material_coverage_fraction(
			values["required_qty"], values["transferred_qty"], precision
		)
		>= 1.0
	}


def _get_candidate_rows():
	work_order = frappe.qb.DocType("Work Order")
	required_item = frappe.qb.DocType("Work Order Item")
	return (
		frappe.qb.from_(work_order)
		.inner_join(required_item)
		.on(required_item.parent == work_order.name)
		.select(
			work_order.name.as_("work_order"),
			work_order.qty,
			required_item.item_code,
			required_item.required_qty,
			required_item.transferred_qty,
		)
		.where(
			(work_order.docstatus == 1)
			& (work_order.status.notin(["Stopped", "Closed", "Completed"]))
			& (fn.Coalesce(work_order.skip_transfer, 0) == 0)
			& (fn.Coalesce(work_order.track_semi_finished_goods, 0) == 0)
			& (fn.Coalesce(work_order.material_transferred_for_manufacturing, 0) < work_order.qty)
			& (fn.Coalesce(work_order.transfer_material_against, "") != "Job Card")
			& (required_item.include_item_in_manufacturing == 1)
			& (required_item.required_qty > 0)
		)
	).run(as_dict=True)
