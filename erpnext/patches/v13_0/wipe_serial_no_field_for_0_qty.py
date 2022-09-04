import frappe


def execute():

	doctype = "Stock Reconciliation Item"

	if not frappe.db.has_column(doctype, "current_serial_no"):
		# nothing to fix if column doesn't exist
		return

	sr_item = frappe.qb.DocType(doctype)

	(
		frappe.qb.update(sr_item).set(sr_item.current_serial_no, None).where(sr_item.current_qty == 0)
	).run()
