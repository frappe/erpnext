import frappe
from frappe.query_builder.functions import IfNull
from frappe.utils import flt
from pypika.terms import ExistsCriterion


def execute():
	updates = {
		row.name: {"output_qty": flt(row.finished_good_qty) * flt(row.qty) / flt(row.bom_qty)}
		for row in get_operations_without_output_qty()
		if flt(row.bom_qty)
	}

	if updates:
		frappe.db.bulk_update("Work Order Operation", updates, update_modified=False)


def get_operations_without_output_qty():
	operation = frappe.qb.DocType("Work Order Operation")
	work_order = frappe.qb.DocType("Work Order")
	bom_operation = frappe.qb.DocType("BOM Operation")
	bom = frappe.qb.DocType("BOM")
	job_card = frappe.qb.DocType("Job Card")

	job_cards = (
		frappe.qb.from_(job_card)
		.select(job_card.name)
		.where((job_card.operation_id == operation.name) & (job_card.docstatus < 2))
	)

	return (
		frappe.qb.from_(operation)
		.inner_join(work_order)
		.on(work_order.name == operation.parent)
		.inner_join(bom_operation)
		.on(bom_operation.name == operation.bom_operation)
		.inner_join(bom)
		.on(bom.name == bom_operation.parent)
		.select(operation.name, bom_operation.finished_good_qty, bom.quantity.as_("bom_qty"), work_order.qty)
		.where(
			(operation.parenttype == "Work Order")
			& (work_order.docstatus < 2)
			& (work_order.track_semi_finished_goods == 1)
			& work_order.status.notin(["Completed", "Closed"])
			& (operation.bom == work_order.bom_no)
			& (IfNull(operation.output_qty, 0) == 0)
			& (bom_operation.finished_good_qty > 0)
			& operation.finished_good.isnotnull()
			& (operation.finished_good != work_order.production_item)
			& ExistsCriterion(job_cards).negate()
		)
	).run(as_dict=True)
