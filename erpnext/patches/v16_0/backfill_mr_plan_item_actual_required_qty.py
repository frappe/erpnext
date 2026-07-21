import frappe


def execute():
	plans = frappe.get_all("Production Plan", filters={"docstatus": 1}, pluck="name")
	if not plans:
		return

	child = frappe.qb.DocType("Material Request Plan Item")
	(
		frappe.qb.update(child)
		.set(child.actual_required_qty, child.quantity)
		.where((child.quantity != 0) & (child.parent.isin(plans)))
	).run()
