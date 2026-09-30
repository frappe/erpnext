import frappe


def execute():
	"""Recalculate billing status of Delivery Notes left open by a return.

	Returning the uninvoiced qty of a Delivery Note did not recalculate the original
	Delivery Note, so it stayed "To Bill" / "Partially Billed" with nothing left to invoice.
	"""
	dn = frappe.qb.DocType("Delivery Note")
	dn_item = frappe.qb.DocType("Delivery Note Item")

	delivery_notes = (
		frappe.qb.from_(dn)
		.inner_join(dn_item)
		.on(dn_item.parent == dn.name)
		.select(dn.name)
		.distinct()
		.where(
			(dn.docstatus == 1)
			& (dn.is_return == 0)
			& dn.status.isin(["To Bill", "Partially Billed"])
			& (dn_item.returned_qty > 0)
		)
		.run(pluck=True)
	)

	for name in delivery_notes:
		doc = frappe.get_doc("Delivery Note", name)
		doc.update_billing_percentage(update_modified=False)
		doc.load_from_db()
		doc.set_status(update=True, update_modified=False)
