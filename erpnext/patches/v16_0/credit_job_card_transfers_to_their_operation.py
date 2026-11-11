import frappe


def execute():
	stock_entry = frappe.qb.DocType("Stock Entry")
	work_order = frappe.qb.DocType("Work Order")

	work_orders = (
		frappe.qb.from_(stock_entry)
		.inner_join(work_order)
		.on(work_order.name == stock_entry.work_order)
		.select(work_order.name)
		.distinct()
		.where(
			(stock_entry.docstatus == 1)
			& (stock_entry.purpose == "Material Transfer for Manufacture")
			& stock_entry.job_card.isnotnull()
			& (work_order.docstatus == 1)
			& work_order.status.notin(["Completed", "Closed"])
		)
	).run(pluck=True)

	for name in work_orders:
		doc = frappe.get_doc("Work Order", name)
		doc.update_transferred_qty_for_required_items()
		doc.update_reserved_qty_for_production()
