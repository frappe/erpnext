import frappe


def execute():
	child = frappe.qb.DocType("Material Request Plan Item")
	frappe.qb.update(child).set(child.actual_required_qty, child.quantity).run()
