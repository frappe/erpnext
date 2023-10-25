import frappe


def execute():
	"""
	1. Get submitted Work Orders with MR, MR Item and SO set
	2. Get SO Item detail from MR Item detail in WO, and set in WO
	3. Update work_order_qty in SO
	"""
	work_order = frappe.qb.DocType("Work Order")
	query = (
		frappe.qb.from_(work_order)
		.select(
			work_order.name,
			work_order.produced_qty,
			work_order.material_request,
			work_order.material_request_item,
			work_order.sales_order,
		)
		.where(
			(work_order.material_request.isnotnull())
			& (work_order.material_request_item.isnotnull())
			& (work_order.sales_order.isnotnull())
			& (work_order.docstatus == 1)
			& (work_order.produced_qty > 0)
		)
	)
	results = query.run(as_dict=True)

	for row in results:
		so_item = frappe.get_value(
			"Material Request Item", row.material_request_item, "sales_order_item"
		)
		frappe.db.set_value("Work Order", row.name, "sales_order_item", so_item)

		if so_item:
			wo = frappe.get_doc("Work Order", row.name)
			wo.update_work_order_qty_in_so()
