import frappe
from frappe.query_builder.functions import Max, Min


def execute():
	stock_entry = frappe.qb.DocType("Stock Entry")
	work_order = frappe.qb.DocType("Work Order")

	work_orders = (
		frappe.qb.from_(stock_entry)
		.inner_join(work_order)
		.on(work_order.name == stock_entry.work_order)
		.select(work_order.name)
		.where(
			(stock_entry.docstatus == 1)
			& (stock_entry.purpose == "Material Transfer for Manufacture")
			& (stock_entry.is_return == 0)
			& (work_order.docstatus == 1)
			& work_order.status.notin(["Completed", "Closed"])
		)
		.groupby(work_order.name)
		.having((Min(stock_entry.fg_completed_qty) == 0) & (Max(stock_entry.fg_completed_qty) > 0))
	).run(pluck=True)

	for name in work_orders:
		frappe.get_doc("Work Order", name).refresh_material_transferred_for_manufacturing()
