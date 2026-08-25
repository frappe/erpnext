import frappe


def execute():
	if not frappe.db.has_column("Sales Order", "skip_delivery_note"):
		return

	so = frappe.qb.DocType("Sales Order")
	soi = frappe.qb.DocType("Sales Order Item")

	exempt_orders = (
		frappe.qb.from_(so)
		.select(so.name)
		.where((so.skip_delivery_note == 1) & (so.docstatus == 1))
		.run(pluck=True)
	)

	if not exempt_orders:
		return

	(
		frappe.qb.update(soi)
		.set(soi.skip_delivery, 1)
		.where((soi.parenttype == "Sales Order") & soi.parent.isin(exempt_orders))
		.run()
	)

	(
		frappe.qb.update(so)
		.set(so.per_delivered, 100)
		.set(so.delivery_status, "Not Applicable")
		.where(so.name.isin(exempt_orders))
		.run()
	)
