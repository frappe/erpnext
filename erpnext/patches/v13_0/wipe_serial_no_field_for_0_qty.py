import frappe


def execute():
	sr_item = frappe.qb.DocType("Stock Reconciliation Item")

	(frappe.qb
		.update(sr_item)
		.set(sr_item.current_serial_no, None)
		.where(sr_item.current_qty == 0)
	).run()
