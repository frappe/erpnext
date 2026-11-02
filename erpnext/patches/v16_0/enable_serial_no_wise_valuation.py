import frappe


def execute():
	item = frappe.qb.DocType("Item")

	(
		frappe.qb.update(item)
		.set(item.use_serial_no_wise_valuation, 1)
		.where((item.has_serial_no == 1) & (item.use_serial_no_wise_valuation == 0))
	).run()
