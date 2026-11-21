import frappe

from erpnext.patches.v16_0.recalculate_returned_delivery_note_billing_status import (
	recalculate_billing_status,
)


def execute():
	"""Recalculate billing status of Delivery Notes with a return in a non-stock UOM.

	Other Delivery Notes of the same Sales Order rows share its billed qty, so they are included too.
	"""
	dn = frappe.qb.DocType("Delivery Note")
	dn_item = frappe.qb.DocType("Delivery Note Item")

	returned_rows = (
		frappe.qb.from_(dn_item)
		.inner_join(dn)
		.on(dn_item.parent == dn.name)
		.select(dn_item.parent, dn_item.so_detail)
		.where(
			(dn.docstatus == 1)
			& (dn.is_return == 0)
			& (dn_item.returned_qty > 0)
			& (dn_item.conversion_factor != 1)
		)
		.run(as_dict=True)
	)

	delivery_notes = {row.parent for row in returned_rows}
	if so_details := {row.so_detail for row in returned_rows if row.so_detail}:
		delivery_notes.update(
			frappe.qb.from_(dn_item)
			.inner_join(dn)
			.on(dn_item.parent == dn.name)
			.select(dn.name)
			.distinct()
			.where((dn.docstatus == 1) & (dn.is_return == 0) & dn_item.so_detail.isin(list(so_details)))
			.run(pluck=True)
		)

	recalculate_billing_status(delivery_notes)
