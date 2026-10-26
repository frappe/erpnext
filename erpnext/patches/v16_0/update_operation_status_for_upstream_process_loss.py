import frappe


def execute():
	for name in frappe.get_all(
		"Work Order",
		filters=[
			["docstatus", "=", 1],
			["status", "in", ["Not Started", "In Process"]],
			["Work Order Operation", "process_loss_qty", ">", 0],
		],
		pluck="name",
		distinct=True,
	):
		work_order = frappe.get_doc("Work Order", name)
		work_order.update_operation_status()
		for operation in work_order.operations:
			operation.db_set("status", operation.status, update_modified=False)
