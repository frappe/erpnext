import frappe


def execute():
	SalesInvoice = frappe.qb.DocType("Sales Invoice")

	query = (
		frappe.qb.update(SalesInvoice)
		.set(SalesInvoice.sales_partner, "")
		.set(SalesInvoice.commission_rate, 0)
		.set(SalesInvoice.total_commission, 0)
		.where(SalesInvoice.is_consolidated == 1)
	)

	# For develop/version-16
	if frappe.db.has_column("Sales Invoice", "is_created_using_pos"):
		query = query.where(SalesInvoice.is_created_using_pos == 0)

	query.run()
