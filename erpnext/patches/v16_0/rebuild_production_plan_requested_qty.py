import frappe

from erpnext.stock.doctype.material_request.material_request import update_plan_item_requested_qty


def execute():
	mr_item = frappe.qb.DocType("Material Request Item")
	plan_item = frappe.qb.DocType("Material Request Plan Item")
	plan_item_names = (
		frappe.qb.from_(mr_item)
		.inner_join(plan_item)
		.on(plan_item.name == mr_item.material_request_plan_item)
		.select(plan_item.name)
		.distinct()
		.where((mr_item.docstatus == 1) & (mr_item.uom != plan_item.uom))
	).run(pluck=True)

	for start in range(0, len(plan_item_names), 500):
		update_plan_item_requested_qty(plan_item_names[start : start + 500])
