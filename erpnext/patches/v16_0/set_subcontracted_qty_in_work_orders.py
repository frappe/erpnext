import frappe

from erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order import update_subcontracted_qty


def execute():
	job_card = frappe.qb.DocType("Job Card")
	order = frappe.qb.DocType("Subcontracting Order")
	order_item = frappe.qb.DocType("Subcontracting Order Item")
	work_order = frappe.qb.DocType("Work Order")

	work_orders = (
		frappe.qb.from_(order_item)
		.inner_join(order)
		.on(order.name == order_item.parent)
		.inner_join(job_card)
		.on(job_card.name == order_item.job_card)
		.inner_join(work_order)
		.on(work_order.name == job_card.work_order)
		.select(work_order.name)
		.distinct()
		.where((order.docstatus == 1) & (work_order.docstatus == 1))
	).run(pluck=True)

	for name in work_orders:
		update_subcontracted_qty(name)
