import frappe
from frappe.query_builder.functions import Coalesce


def execute():
	job_card = frappe.qb.DocType("Job Card")
	work_order = frappe.qb.DocType("Work Order")
	wo_operation = frappe.qb.DocType("Work Order Operation")
	bom_operation = frappe.qb.DocType("BOM Operation")
	workstation = frappe.qb.DocType("Workstation")

	rows = (
		frappe.qb.from_(job_card)
		.inner_join(work_order)
		.on(work_order.name == job_card.work_order)
		.inner_join(wo_operation)
		.on(wo_operation.name == job_card.operation_id)
		.inner_join(bom_operation)
		.on(
			(bom_operation.parent == Coalesce(wo_operation.bom, work_order.bom_no))
			& (bom_operation.operation == wo_operation.operation)
		)
		.inner_join(workstation)
		.on(workstation.name == job_card.workstation)
		.select(job_card.name, workstation.hour_rate)
		.distinct()
		.where(
			(job_card.docstatus == 1)
			& (Coalesce(job_card.is_corrective_job_card, 0) == 0)
			& (job_card.workstation != bom_operation.workstation)
			& (job_card.hour_rate != workstation.hour_rate)
			& work_order.status.notin(["Completed", "Closed", "Cancelled"])
		)
	).run(as_dict=True)

	for row in rows:
		frappe.db.set_value("Job Card", row.name, "hour_rate", row.hour_rate, update_modified=False)
